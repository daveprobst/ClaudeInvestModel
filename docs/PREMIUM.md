# Premium regions (`/region`)

The free page is unchanged. `/region` is a separate route of the same single-page app, backed by a small Node
service (`server/`) that holds the paid data and decides who may see it.

## How it works

```
browser ──► static site (free)  /, /region           (React)
   │
   └─────► bulwark-api (Node)   /api/*                 token-gated
                                 ├─ POST /api/demo/start        demo token, no payment (24 h)
                                 ├─ POST /api/checkout          Stripe Checkout (subscription) – TEST mode
                                 ├─ POST /api/checkout/confirm  verifies the session with Stripe → member token
                                 ├─ POST /api/login-link        e-mail a sign-in link (needs Resend)
                                 ├─ GET  /api/region/ch         Swiss results – 401 without a valid token
                                 └─ POST /api/portal            Stripe billing portal
```

* **No database.** Stripe is the source of truth. A member token carries the subscription id; every request re-checks
  with Stripe (cached 5 minutes), so a cancelled subscription loses access.
* **Tokens** are HMAC-SHA256 signed (`JWT_SECRET`), sent as `Authorization: Bearer`, stored in `localStorage`.
* **Region data** lives in `server/private/regions/*.json`, produced by `python -m model.run`, and is never copied into
  the public static bundle.
* **Safety rails:** live Stripe keys are refused unless `ALLOW_LIVE=true`; rate limits; CORS limited to `SITE_URL`;
  the magic-link endpoint never reveals whether an e-mail has an account.

## Modes

| `STRIPE_SECRET_KEY` | `DEMO_ENABLED` | What visitors see |
|---|---|---|
| empty | true (default) | "Try the demo — no payment" only |
| `sk_test_…` | true | Subscribe with test card **and** demo access |
| `sk_test_…` | false | Subscribe with test card only |

Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

## Before charging real money (not done)

1. **Make the repository private** (or generate region data at deploy time): `server/private/` is in this public repo,
   so the demo data is readable by anyone.
2. Legal review: selling signals can count as investment advice (FINMA / MiFID), plus VAT (use Stripe Tax), terms, privacy.
3. Use a paid Render instance (free ones sleep after ~15 min) and a verified e-mail domain for Resend.
4. Switch to live keys + `ALLOW_LIVE=true`.

## Adding a region

Implement a `RegionSpec` + input loader in `model/regions.py` (native series where free data exist, labelled U.S.
substitutes elsewhere), add it to `REGIONS`, extend `model/tests/test_region.py`, run `python -m model.run`.
