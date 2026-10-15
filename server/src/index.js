import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Stripe from 'stripe'
import { createApp } from './app.js'
import { loadConfig } from './config.js'
import { makeBilling } from './billing.js'
import { makeMailer } from './mailer.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const dir = path.join(here, '..', 'private', 'regions')
const regions = {}
for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) {
  if (f.endsWith('.json')) { const r = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); regions[r.id] = r }
}

const config = loadConfig()
for (const w of config.warnings) console.warn('[config]', w)
const billing = config.stripeKey ? makeBilling({ stripe: new Stripe(config.stripeKey), config }) : null
const app = createApp({ config, billing, mailer: makeMailer(config), regions })
app.listen(config.port, () => {
  console.log(`bulwark-api on :${config.port} | regions: ${Object.keys(regions).join(', ') || 'none'} | stripe: ${billing ? (config.stripeTestMode ? 'TEST mode' : 'LIVE') : 'off'} | demo: ${config.demoEnabled}`)
})
