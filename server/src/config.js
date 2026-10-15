import crypto from 'node:crypto'

const bool = (v, d) => (v == null || v === '' ? d : /^(1|true|yes)$/i.test(v))

export function loadConfig(env = process.env) {
  const siteUrl = (env.SITE_URL || 'http://localhost:5173').replace(/\/$/, '')
  const key = env.STRIPE_SECRET_KEY || ''
  const live = key.startsWith('sk_live_')
  const allowLive = bool(env.ALLOW_LIVE, false)
  // Safety: while this is a demo, refuse live Stripe keys unless explicitly allowed.
  const stripeKey = key && (!live || allowLive) ? key : ''
  const warnings = []
  if (live && !allowLive) warnings.push('STRIPE_SECRET_KEY is a LIVE key and ALLOW_LIVE is not set: Stripe is disabled.')
  if (key && !live && !key.startsWith('sk_test_')) warnings.push('STRIPE_SECRET_KEY does not look like a Stripe secret key.')
  let jwtSecret = env.JWT_SECRET
  if (!jwtSecret) { jwtSecret = crypto.randomBytes(32).toString('hex'); warnings.push('JWT_SECRET not set: using a random one (sessions reset on restart).') }
  const origins = new Set([siteUrl, ...(env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean)])
  if (!env.NODE_ENV || env.NODE_ENV !== 'production') { origins.add('http://localhost:5173'); origins.add('http://127.0.0.1:5173') }
  return {
    port: Number(env.PORT || 8787),
    siteUrl,
    origins,
    stripeKey,
    stripeTestMode: stripeKey.startsWith('sk_test_'),
    priceId: env.STRIPE_PRICE_ID || '',
    price: { amount: Number(env.PRICE_AMOUNT || 900), currency: (env.PRICE_CURRENCY || 'chf').toLowerCase(), interval: 'month' },
    jwtSecret,
    demoEnabled: bool(env.DEMO_ENABLED, true),
    demoTtlSeconds: Number(env.DEMO_TTL_SECONDS || 24 * 3600),
    sessionTtlSeconds: Number(env.SESSION_TTL_SECONDS || 7 * 24 * 3600),
    resendKey: env.RESEND_API_KEY || '',
    mailFrom: env.MAIL_FROM || 'Bulwark <onboarding@resend.dev>',
    warnings,
  }
}
