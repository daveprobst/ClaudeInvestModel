/** Thin wrapper around the Stripe SDK. State lives in Stripe (no database): entitlement = an active subscription. */
const ACTIVE = new Set(['active', 'trialing'])

export function makeBilling({ stripe, config }) {
  const lineItem = config.priceId
    ? { price: config.priceId, quantity: 1 }
    : {
        quantity: 1,
        price_data: {
          currency: config.price.currency, unit_amount: config.price.amount, recurring: { interval: config.price.interval },
          product_data: { name: 'Bulwark Premium – regional models (test mode demo)' },
        },
      }
  const cache = new Map() // subscription id -> { active, at }

  return {
    async createCheckout({ email }) {
      const s = await stripe.checkout.sessions.create({
        mode: 'subscription',
        line_items: [lineItem],
        success_url: `${config.siteUrl}/region?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${config.siteUrl}/region?canceled=1`,
        allow_promotion_codes: true,
        ...(email ? { customer_email: email } : {}),
      })
      return { url: s.url, id: s.id }
    },

    /** After redirect from Checkout: verify with Stripe that the session really completed with an active subscription. */
    async confirmCheckout(sessionId) {
      if (typeof sessionId !== 'string' || !/^cs_[A-Za-z0-9_]+$/.test(sessionId)) return null
      const s = await stripe.checkout.sessions.retrieve(sessionId, { expand: ['subscription'] })
      const sub = s.subscription
      if (s.status !== 'complete' || !sub || typeof sub === 'string' || !ACTIVE.has(sub.status)) return null
      return { customer: typeof s.customer === 'string' ? s.customer : s.customer?.id, subscription: sub.id, email: s.customer_details?.email || s.customer_email || null }
    },

    async isActive(subscriptionId, ttlMs = 5 * 60 * 1000, now = Date.now()) {
      const hit = cache.get(subscriptionId)
      if (hit && now - hit.at < ttlMs) return hit.active
      const sub = await stripe.subscriptions.retrieve(subscriptionId)
      const active = ACTIVE.has(sub.status)
      cache.set(subscriptionId, { active, at: now })
      return active
    },

    async portal(customer) {
      const s = await stripe.billingPortal.sessions.create({ customer, return_url: `${config.siteUrl}/region` })
      return s.url
    },

    /** Find an active subscription for an e-mail address (for "restore access"). */
    async findActiveByEmail(email) {
      const customers = await stripe.customers.list({ email, limit: 5 })
      for (const c of customers.data) {
        const subs = await stripe.subscriptions.list({ customer: c.id, status: 'all', limit: 10 })
        const hit = subs.data.find((s) => ACTIVE.has(s.status))
        if (hit) return { customer: c.id, subscription: hit.id, email }
      }
      return null
    },
  }
}
