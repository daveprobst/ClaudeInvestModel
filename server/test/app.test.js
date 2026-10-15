import test from 'node:test'
import assert from 'node:assert/strict'
import { createApp } from '../src/app.js'
import { loadConfig } from '../src/config.js'
import { makeBilling } from '../src/billing.js'
import { signToken, verifyToken } from '../src/tokens.js'

const regions = { ch: { id: 'ch', name: 'Switzerland', currency: 'CHF', snapshot: { asof: '2026-09' }, secret: 'PREMIUM-DATA' } }

function fakeStripe({ subStatus = 'active', sessionStatus = 'complete' } = {}) {
  const state = { subStatus, calls: [] }
  return {
    state,
    checkout: { sessions: {
      create: async (a) => { state.calls.push(['create', a]); return { id: 'cs_test_1', url: 'https://checkout.stripe.test/c/pay/cs_test_1' } },
      retrieve: async (id) => ({ id, status: sessionStatus, customer: 'cus_1', customer_details: { email: 'a@b.ch' }, subscription: { id: 'sub_1', status: state.subStatus } }),
    } },
    subscriptions: { retrieve: async () => ({ status: state.subStatus }), list: async () => ({ data: [{ id: 'sub_1', status: state.subStatus }] }) },
    customers: { list: async () => ({ data: [{ id: 'cus_1' }] }) },
    billingPortal: { sessions: { create: async () => ({ url: 'https://billing.stripe.test/p/1' }) } },
  }
}

async function start({ stripe, env = {}, mailer } = {}) {
  const config = loadConfig({ SITE_URL: 'https://site.test', JWT_SECRET: 's3cret', NODE_ENV: 'production', ...env })
  const sent = []
  const m = mailer || { sendLoginLink: async (to, link) => { sent.push({ to, link }); return true } }
  const app = createApp({ config, billing: stripe ? makeBilling({ stripe, config }) : null, mailer: m, regions })
  const server = await new Promise((r) => { const s = app.listen(0, () => r(s)) })
  const base = `http://127.0.0.1:${server.address().port}`
  const call = (path, { method = 'GET', body, token, origin } = {}) => fetch(base + path, {
    method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(origin ? { Origin: origin } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return { call, sent, close: () => server.close(), config }
}

test('tokens: sign, verify, tamper, expire', () => {
  const t = signToken({ plan: 'demo' }, 'k', 60)
  assert.equal(verifyToken(t, 'k').plan, 'demo')
  assert.equal(verifyToken(t, 'other'), null)
  const [h, b, s] = t.split('.')
  assert.equal(verifyToken(`${h}.${Buffer.from(JSON.stringify({ plan: 'premium', exp: 9e9 })).toString('base64url')}.${s}`, 'k'), null)
  assert.equal(verifyToken(t, 'k', Date.now() + 61_000), null)
  assert.equal(verifyToken('garbage', 'k'), null)
  assert.equal(verifyToken(`${h}.${b}.`, 'k'), null)
})

test('region data is locked without a token and with bad tokens', async () => {
  const s = await start()
  assert.equal((await s.call('/api/region/ch')).status, 401)
  assert.equal((await s.call('/api/region/ch', { token: 'nope' })).status, 401)
  const forged = signToken({ plan: 'premium', subid: 'sub_1' }, 'wrong-secret', 3600)
  assert.equal((await s.call('/api/region/ch', { token: forged })).status, 401)
  s.close()
})

test('config is public and does not leak data', async () => {
  const s = await start()
  const j = await (await s.call('/api/config')).json()
  assert.equal(j.stripe, false); assert.equal(j.demo, true); assert.deepEqual(j.regions.map((r) => r.id), ['ch'])
  assert.ok(!JSON.stringify(j).includes('PREMIUM-DATA'))
  s.close()
})

test('demo flow grants access, and can be disabled', async () => {
  const s = await start()
  const { token, plan } = await (await s.call('/api/demo/start', { method: 'POST' })).json()
  assert.equal(plan, 'demo')
  const r = await (await s.call('/api/region/ch', { token })).json()
  assert.equal(r.secret, 'PREMIUM-DATA'); assert.equal(r.access.demo, true)
  assert.equal((await s.call('/api/portal', { method: 'POST', token })).status, 400)
  s.close()
  const off = await start({ env: { DEMO_ENABLED: 'false' } })
  assert.equal((await off.call('/api/demo/start', { method: 'POST' })).status, 404)
  const stale = signToken({ plan: 'demo' }, 's3cret', 3600)
  assert.equal((await off.call('/api/region/ch', { token: stale })).status, 401)
  off.close()
})

test('stripe checkout: create session, confirm, access, cancellation revokes', async () => {
  const stripe = fakeStripe()
  const s = await start({ stripe })
  const c = await (await s.call('/api/checkout', { method: 'POST', body: { email: 'a@b.ch' } })).json()
  assert.match(c.url, /checkout\.stripe\.test/)
  const args = stripe.state.calls[0][1]
  assert.equal(args.mode, 'subscription'); assert.equal(args.customer_email, 'a@b.ch')
  assert.equal(args.line_items[0].price_data.currency, 'chf')
  assert.equal(args.success_url, 'https://site.test/region?session_id={CHECKOUT_SESSION_ID}')
  const ok = await (await s.call('/api/checkout/confirm', { method: 'POST', body: { session_id: 'cs_test_1' } })).json()
  assert.equal(ok.plan, 'premium')
  assert.equal((await s.call('/api/region/ch', { token: ok.token })).status, 200)
  assert.equal(((await (await s.call('/api/portal', { method: 'POST', token: ok.token })).json()).url), 'https://billing.stripe.test/p/1')
  s.close()
})

test('stripe: unpaid sessions and bad ids are rejected', async () => {
  const s = await start({ stripe: fakeStripe({ sessionStatus: 'open' }) })
  assert.equal((await s.call('/api/checkout/confirm', { method: 'POST', body: { session_id: 'cs_test_1' } })).status, 402)
  assert.equal((await s.call('/api/checkout/confirm', { method: 'POST', body: { session_id: '../../etc' } })).status, 402)
  assert.equal((await s.call('/api/checkout/confirm', { method: 'POST', body: {} })).status, 402)
  s.close()
  const none = await start()
  assert.equal((await none.call('/api/checkout', { method: 'POST', body: {} })).status, 503)
  none.close()
})

test('canceled subscription loses access', async () => {
  const stripe = fakeStripe()
  const s = await start({ stripe })
  const { token } = await (await s.call('/api/checkout/confirm', { method: 'POST', body: { session_id: 'cs_test_1' } })).json()
  stripe.state.subStatus = 'canceled'
  // entitlement is cached for 5 minutes, so build a fresh server to simulate the cache expiring
  const s2 = await start({ stripe })
  assert.equal((await s2.call('/api/region/ch', { token })).status, 403)
  s.close(); s2.close()
})

test('magic link: sends only for active customers, never reveals existence, single-purpose token', async () => {
  const stripe = fakeStripe()
  const s = await start({ stripe })
  const r = await s.call('/api/login-link', { method: 'POST', body: { email: 'a@b.ch' } })
  assert.deepEqual(await r.json(), { ok: true })
  await new Promise((r2) => setTimeout(r2, 50))
  assert.equal(s.sent.length, 1)
  const magic = new URL(s.sent[0].link).searchParams.get('login')
  assert.equal((await s.call('/api/region/ch', { token: magic })).status, 401)   // magic token is not a session
  const v = await (await s.call('/api/login/verify', { method: 'POST', body: { token: magic } })).json()
  assert.equal(v.plan, 'premium')
  assert.equal((await s.call('/api/region/ch', { token: v.token })).status, 200)
  assert.equal((await s.call('/api/login/verify', { method: 'POST', body: { token: 'x' } })).status, 401)
  const bad = await s.call('/api/login-link', { method: 'POST', body: { email: 'not-an-email' } })
  assert.deepEqual(await bad.json(), { ok: true }); await new Promise((r2) => setTimeout(r2, 30)); assert.equal(s.sent.length, 1)
  s.close()
})

test('CORS only for allowed origins; OPTIONS answered', async () => {
  const s = await start()
  const ok = await s.call('/api/health', { origin: 'https://site.test' })
  assert.equal(ok.headers.get('access-control-allow-origin'), 'https://site.test')
  const bad = await s.call('/api/health', { origin: 'https://evil.test' })
  assert.equal(bad.headers.get('access-control-allow-origin'), null)
  assert.equal((await s.call('/api/region/ch', { method: 'OPTIONS', origin: 'https://site.test' })).status, 204)
  s.close()
})

test('live Stripe keys are refused unless ALLOW_LIVE is set', () => {
  assert.equal(loadConfig({ STRIPE_SECRET_KEY: 'sk_live_abc' }).stripeKey, '')
  assert.equal(loadConfig({ STRIPE_SECRET_KEY: 'sk_live_abc', ALLOW_LIVE: 'true' }).stripeKey, 'sk_live_abc')
  const t = loadConfig({ STRIPE_SECRET_KEY: 'sk_test_abc' }); assert.equal(t.stripeKey, 'sk_test_abc'); assert.equal(t.stripeTestMode, true)
})

test('rate limit on login-link', async () => {
  const s = await start({ stripe: fakeStripe() })
  let last = 200
  for (let i = 0; i < 8; i++) last = (await s.call('/api/login-link', { method: 'POST', body: { email: 'a@b.ch' } })).status
  assert.equal(last, 429)
  s.close()
})
