import express from 'express'
import crypto from 'node:crypto'
import { signToken, verifyToken } from './tokens.js'

const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/

/** Tiny fixed-window limiter, per IP + bucket. Good enough for a demo behind Render's proxy. */
function limiter(max, windowMs = 60_000) {
  const hits = new Map()
  return (req, res, next) => {
    const key = `${req.ip}|${req.baseUrl}${req.path}`
    const now = Date.now()
    const e = hits.get(key)
    if (!e || now - e.t > windowMs) hits.set(key, { t: now, n: 1 })
    else if (++e.n > max) return res.status(429).json({ error: 'Too many requests, slow down.' })
    if (hits.size > 5000) for (const [k, v] of hits) if (now - v.t > windowMs) hits.delete(k)
    next()
  }
}

/**
 * @param {{config: object, billing: object|null, mailer: object, regions: Record<string, any>}} deps
 */
export function createApp({ config, billing, mailer, regions }) {
  const app = express()
  app.set('trust proxy', 1)
  app.disable('x-powered-by')

  // ---- CORS (Bearer tokens, no cookies) + security headers ----
  app.use((req, res, next) => {
    const origin = req.headers.origin
    if (origin && config.origins.has(origin)) {
      res.set('Access-Control-Allow-Origin', origin)
      res.set('Vary', 'Origin')
      res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type')
      res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
      res.set('Access-Control-Max-Age', '600')
    }
    res.set('X-Content-Type-Options', 'nosniff')
    res.set('Cache-Control', 'no-store')
    if (req.method === 'OPTIONS') return res.status(204).end()
    next()
  })
  app.use(express.json({ limit: '10kb' }))
  app.use('/api', limiter(120))

  const issue = (claims, ttl) => signToken(claims, config.jwtSecret, ttl)
  const publicRegions = Object.values(regions).map((r) => ({ id: r.id, name: r.name, currency: r.currency, asof: r.snapshot.asof }))

  // ---- public ----
  app.get('/api/health', (_req, res) => res.json({ ok: true }))
  app.get('/api/config', (_req, res) => res.json({
    stripe: Boolean(billing), testMode: billing ? config.stripeTestMode : true, demo: config.demoEnabled,
    price: config.price, regions: publicRegions, mail: Boolean(config.resendKey),
  }))

  // ---- demo access: no payment, clearly a demo token ----
  app.post('/api/demo/start', limiter(20), (_req, res) => {
    if (!config.demoEnabled) return res.status(404).json({ error: 'Demo access is disabled.' })
    const token = issue({ sub: crypto.randomUUID(), plan: 'demo' }, config.demoTtlSeconds)
    res.json({ token, plan: 'demo', expiresIn: config.demoTtlSeconds })
  })

  // ---- Stripe checkout ----
  app.post('/api/checkout', limiter(10), async (req, res) => {
    if (!billing) return res.status(503).json({ error: 'Card payments are not configured on this server.' })
    const email = typeof req.body?.email === 'string' && EMAIL.test(req.body.email) ? req.body.email : undefined
    try { res.json(await billing.createCheckout({ email })) }
    catch (e) { console.error('checkout failed', e.message); res.status(502).json({ error: 'Could not start checkout.' }) }
  })

  app.post('/api/checkout/confirm', limiter(20), async (req, res) => {
    if (!billing) return res.status(503).json({ error: 'Card payments are not configured on this server.' })
    try {
      const got = await billing.confirmCheckout(req.body?.session_id)
      if (!got) return res.status(402).json({ error: 'Payment not completed.' })
      const token = issue({ sub: got.customer, plan: 'premium', cus: got.customer, subid: got.subscription, email: got.email }, config.sessionTtlSeconds)
      res.json({ token, plan: 'premium', email: got.email, expiresIn: config.sessionTtlSeconds })
    } catch (e) { console.error('confirm failed', e.message); res.status(502).json({ error: 'Could not verify payment.' }) }
  })

  // ---- restore access by e-mail (magic link). Always answers ok: no account enumeration. ----
  app.post('/api/login-link', limiter(5), async (req, res) => {
    res.json({ ok: true })
    if (!billing) return
    const email = req.body?.email
    if (typeof email !== 'string' || !EMAIL.test(email)) return
    try {
      const found = await billing.findActiveByEmail(email.trim().toLowerCase())
      if (!found) return
      const magic = issue({ purpose: 'magic', cus: found.customer, subid: found.subscription, email: found.email }, 15 * 60)
      await mailer.sendLoginLink(found.email, `${config.siteUrl}/region?login=${magic}`)
    } catch (e) { console.error('login-link failed', e.message) }
  })

  app.post('/api/login/verify', limiter(20), async (req, res) => {
    const c = verifyToken(req.body?.token, config.jwtSecret)
    if (!billing || !c || c.purpose !== 'magic' || !(await billing.isActive(c.subid, 0))) return res.status(401).json({ error: 'Link invalid or expired.' })
    const token = issue({ sub: c.cus, plan: 'premium', cus: c.cus, subid: c.subid, email: c.email }, config.sessionTtlSeconds)
    res.json({ token, plan: 'premium', email: c.email, expiresIn: config.sessionTtlSeconds })
  })

  // ---- authenticated ----
  const auth = async (req, res, next) => {
    const m = /^Bearer (.+)$/.exec(req.headers.authorization || '')
    const c = m && verifyToken(m[1], config.jwtSecret)
    if (!c || c.purpose === 'magic' || !['demo', 'premium'].includes(c.plan)) return res.status(401).json({ error: 'Sign in required.' })
    if (c.plan === 'demo' && !config.demoEnabled) return res.status(401).json({ error: 'Demo access is disabled.' })
    if (c.plan === 'premium') {
      try {
        if (!billing || !(await billing.isActive(c.subid))) return res.status(403).json({ error: 'Subscription is not active.' })
      } catch (e) { console.error('subscription check failed', e.message); return res.status(502).json({ error: 'Could not verify subscription.' }) }
    }
    req.claims = c
    next()
  }

  app.get('/api/me', auth, (req, res) => res.json({ plan: req.claims.plan, email: req.claims.email || null, expires: req.claims.exp }))

  app.get('/api/region/:id', auth, (req, res) => {
    const r = regions[req.params.id]
    if (!r) return res.status(404).json({ error: 'Unknown region.' })
    res.json({ ...r, access: { plan: req.claims.plan, demo: req.claims.plan === 'demo' } })
  })

  app.post('/api/portal', auth, async (req, res) => {
    if (req.claims.plan !== 'premium' || !billing) return res.status(400).json({ error: 'No billing account (demo access).' })
    try { res.json({ url: await billing.portal(req.claims.cus) }) }
    catch (e) { console.error('portal failed', e.message); res.status(502).json({ error: 'Could not open billing portal.' }) }
  })

  app.use('/api', (_req, res) => res.status(404).json({ error: 'Not found.' }))
  app.use((err, _req, res, _next) => { console.error(err.message); res.status(err.status === 400 ? 400 : 500).json({ error: 'Request failed.' }) })
  return app
}
