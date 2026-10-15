import { useEffect, useMemo, useState } from 'react'
import { api, ApiError, getConfig, tokenStore, type Config } from '../api'
import type { RegionPayload } from '../types'
import { Gauge } from '../charts/Gauge'
import { Sparkline } from '../charts/Sparkline'
import { Performance } from './Performance'
import { Crashes } from './Crashes'
import { Icon, Reveal, Section, Status } from './ui'
import { monthLabel, num, pct, regimeLabel } from '../format'

const CH_NAMES: Record<string, string> = {
  '1980-12': 'Early-80s recession', '1987-09': 'Black Monday', '1989-08': 'Early-90s bear market', '1998-07': 'Russia / LTCM crisis',
  '2000-08': 'Dot-com bust', '2007-05': 'Global financial crisis', '2020-02': 'COVID crash', '2021-12': 'Inflation & rate shock',
}

/* ──────────────────────────────── page controller ──────────────────────────────── */
export function RegionPage() {
  const [cfg, setCfg] = useState<Config | null>(null)
  const [waking, setWaking] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(tokenStore.get())
  const [data, setData] = useState<RegionPayload | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { getConfig(() => setWaking(true)).then(setCfg).catch((e) => setErr(String(e.message || e))).finally(() => setWaking(false)) }, [])

  // returning from Stripe Checkout / magic link
  useEffect(() => {
    if (!cfg) return
    const q = new URLSearchParams(window.location.search)
    const clean = () => window.history.replaceState({}, '', '/region')
    const sid = q.get('session_id'), login = q.get('login')
    if (q.get('canceled')) { setNotice('Checkout was cancelled — nothing was charged.'); clean() }
    if (sid) {
      setBusy(true); clean()
      api.confirm(sid).then((s) => { tokenStore.set(s.token); setToken(s.token); setNotice('Payment confirmed — welcome to Bulwark Premium (Stripe test mode).') })
        .catch((e) => setNotice(`We could not confirm the payment: ${e.message}`)).finally(() => setBusy(false))
    } else if (login) {
      setBusy(true); clean()
      api.verify(login).then((s) => { tokenStore.set(s.token); setToken(s.token) }).catch((e) => setNotice(e.message)).finally(() => setBusy(false))
    }
  }, [cfg])

  useEffect(() => {
    if (!token) { setData(null); return }
    let alive = true
    api.region('ch', token).then((d) => alive && setData(d)).catch((e) => {
      if (!alive) return
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) { tokenStore.clear(); setToken(null); setNotice(e.status === 403 ? 'Your subscription is no longer active.' : 'Your session expired — please sign in again.') }
      else setErr(e.message)
    })
    return () => { alive = false }
  }, [token])

  const signOut = () => { tokenStore.clear(); setToken(null); setData(null) }

  if (err) return <div className="wrap skeleton" role="alert">Couldn’t reach the premium server. {err}<br /><button className="btn mt" onClick={() => window.location.reload()}>Try again</button></div>
  if (!cfg) return <div className="skeleton">{waking ? <Waking /> : 'Loading…'}</div>
  if (busy) return <div className="skeleton">Verifying…</div>
  if (token && !data) return <div className="skeleton">Loading your region…</div>
  if (token && data) return <Dashboard data={data} cfg={cfg} token={token} signOut={signOut} notice={notice} />
  return <Paywall cfg={cfg} notice={notice} onSession={(s) => { tokenStore.set(s.token); setToken(s.token); setNotice(null) }} />
}

function Waking() {
  return <div style={{ textAlign: 'center', maxWidth: 420 }}>
    <div style={{ fontWeight: 650, color: 'var(--ink)', marginBottom: 6 }}>Waking up the premium server…</div>
    <div>The free hosting tier sleeps when idle; the first visit can take up to a minute.</div>
  </div>
}

/* ──────────────────────────────── paywall ──────────────────────────────── */
function Paywall({ cfg, notice, onSession }: { cfg: Config; notice: string | null; onSession: (s: { token: string; plan: 'demo' | 'premium' }) => void }) {
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState<string | null>(notice)
  const [loading, setLoading] = useState<string | null>(null)
  const [restore, setRestore] = useState(false)
  const price = `${cfg.price.currency.toUpperCase()} ${(cfg.price.amount / 100).toFixed(2).replace(/\.00$/, '')}`

  const run = async (name: string, fn: () => Promise<void>) => {
    setLoading(name); setMsg(null)
    try { await fn() } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) } finally { setLoading(null) }
  }
  const demo = () => run('demo', async () => onSession(await api.demo()))
  const pay = () => run('pay', async () => { const { url } = await api.checkout(email || undefined); window.location.href = url })
  const sendLink = () => run('link', async () => { await api.loginLink(email); setMsg('If that e-mail has an active subscription, a sign-in link is on its way.') })

  return (
    <div className="wrap">
      <header className="hero" style={{ paddingBottom: 8 }}>
        <span className="pill"><i className="dot" style={{ background: 'var(--warn)', boxShadow: '0 0 0 4px color-mix(in srgb, var(--warn) 22%, transparent)' }} /> Premium · regional models</span>
        <h1 style={{ fontSize: 'clamp(34px, 5.6vw, 58px)' }}>Run Bulwark on <span className="grad">your market.</span></h1>
        <p className="lead" style={{ color: 'var(--ink-2)', fontSize: 19, maxWidth: 680 }}>
          Everything on the main page stays free. Premium runs the same fixed, leak-tested rules on your home market — with its own prices, rates and yield curve —
          and is honest about every input that had to be borrowed from the U.S.
        </p>
      </header>

      {msg && <div className="callout info" role="status" style={{ marginBottom: 18 }}>{msg}</div>}

      <div className="paywall-grid">
        <div className="card">
          <div className="eyebrow">Available now</div>
          <h2 style={{ fontSize: 30, margin: '12px 0 8px' }}>🇨🇭 Switzerland <span className="tag neutral" style={{ verticalAlign: 'middle' }}>demo region</span></h2>
          <p className="lede">Swiss share index, Swiss cash rate and Swiss yield curve, in CHF. Valuation (CAPE, Buffett indicator) has no free Swiss source, so the <b>U.S. series is substituted and labelled</b> wherever it appears.</p>
          <ul className="clean mt2" style={{ marginTop: 20 }}>
            <li><b>Live signal</b> — today’s recommended equity exposure for the Swiss market, with trip-wire distances.</li>
            <li><b>Full backtest since 1975</b> — growth, drawdown, exposure, crash scorecard, calendar years.</li>
            <li><b>Reality check</b> — ablations, dividend-assumption sensitivity, block bootstrap. Including where it works <i>less</i> well than in the U.S.</li>
            <li><b>Provenance panel</b> — which inputs are Swiss, which are U.S. stand-ins, which are assumptions.</li>
          </ul>
          <div className="locked mt2" aria-hidden>
            <div className="locked-bars"><i style={{ height: '38%' }} /><i style={{ height: '52%' }} /><i style={{ height: '46%' }} /><i style={{ height: '70%' }} /><i style={{ height: '62%' }} /><i style={{ height: '88%' }} /><i style={{ height: '80%' }} /></div>
            <div className="locked-badge">{Icon.lock}<span>Members only</span></div>
          </div>
        </div>

        <div className="card pricing">
          <div className="eyebrow">Membership</div>
          <div className="price"><span className="mono">{price}</span><small> / month</small></div>
          <div className="sub">Demo price · cancel any time · more regions are planned.</div>

          {cfg.testMode && (
            <div className="demo-banner" role="note"><b>TEST MODE.</b> No real money moves. {cfg.stripe ? <>Pay with Stripe’s test card <span className="mono">4242 4242 4242 4242</span>, any future expiry, any CVC.</> : 'Card payments are switched off on this server; use the demo access below.'}</div>
          )}

          {cfg.stripe && (
            <>
              <label className="field">E-mail (optional, pre-fills checkout)
                <input className="input" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
              </label>
              <button className="btn primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading !== null} onClick={pay}>{loading === 'pay' ? 'Opening Stripe…' : 'Subscribe with card'}</button>
            </>
          )}
          {cfg.demo && (
            <button className={`btn ${cfg.stripe ? '' : 'primary'}`} style={{ width: '100%', justifyContent: 'center', marginTop: cfg.stripe ? 10 : 18 }} disabled={loading !== null} onClick={demo}>
              {loading === 'demo' ? 'Starting…' : 'Try the demo — no payment'}
            </button>
          )}
          {cfg.demo && <div className="sub" style={{ marginTop: 8 }}>Demo access lasts 24 hours on this device and is clearly marked inside.</div>}
          {!cfg.stripe && !cfg.demo && <div className="callout">Premium sign-up is not open yet.</div>}

          {cfg.stripe && (
            <div style={{ marginTop: 18 }}>
              <button className="toggle-link" onClick={() => setRestore((r) => !r)}>Already a member? Restore access</button>
              {restore && (
                <div className="mt">
                  <input className="input" type="email" placeholder="Your subscription e-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
                  <button className="btn" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} disabled={loading !== null || !email} onClick={sendLink}>E-mail me a sign-in link</button>
                  {!cfg.mail && <div className="sub" style={{ marginTop: 6 }}>E-mail sending is not configured on this server yet.</div>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <p className="sub" style={{ marginTop: 18, maxWidth: 760 }}>Research and education only — not investment advice. Real payments are not enabled; this is a demonstration of the membership flow.</p>
    </div>
  )
}

/* ──────────────────────────────── dashboard ──────────────────────────────── */
const ORIGIN_TAG: Record<string, { cls: string; text: string }> = {
  native: { cls: 'ok', text: 'Swiss data' }, substitute: { cls: 'rich', text: 'U.S. substitute' }, assumption: { cls: 'neutral', text: 'Assumption' },
}

function Dashboard({ data, cfg, token, signOut, notice }: { data: RegionPayload; cfg: Config; token: string; signOut: () => void; notice: string | null }) {
  const s = data.snapshot
  const full = data.headline.full
  const m = full.metrics
  const [pk, setPk] = useState<'full' | 'since1990' | 'since2010' | 'lost_decades'>('full')
  const P = data.headline[pk]
  const b = P.metrics.bulwark, h = P.metrics.buyhold
  const first = data.first.slice(0, 4)
  const stepPct = Math.round(s.step * 100)
  const starts = useMemo(() => [{ y: Number(first), label: first }, { y: 1990, label: '1990' }, { y: 2000, label: '2000 (dot-com)' }, { y: 2007, label: '2007 (GFC)' }, { y: 2010, label: '2010' }], [first])
  const sinceFirst = (k: string) => (k === 'full' ? `${first} – today` : data.headline[k].label)
  const portal = async () => { try { window.location.href = (await api.portal(token)).url } catch (e) { alert(e instanceof Error ? e.message : String(e)) } }
  const ab = data.ablations
  const diff = m.buyhold.cagr - m.bulwark.cagr

  return (
    <>
      <div className="wrap">
        <header className="hero" style={{ paddingBottom: 0 }}>
          <div className="range-row">
            <div>
              <span className="pill"><i className="dot" /> {data.access.demo ? 'Demo access · no payment taken' : 'Premium member'}</span>
              <h1 style={{ fontSize: 'clamp(34px, 5.4vw, 56px)', marginTop: 18 }}>🇨🇭 Bulwark for <span className="grad">Switzerland</span></h1>
              <p className="lede" style={{ maxWidth: 680, marginTop: 10 }}>Same fixed rules as the U.S. model, run on Swiss prices, rates and yield curve, in {data.currency}. Signal for the {monthLabel(s.asof)} close.</p>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div className="seg" role="group" aria-label="Region"><button aria-pressed>Switzerland</button><button disabled title="More regions are on the way">More soon</button></div>
              {data.access.plan === 'premium' && cfg.stripe && <button className="btn" onClick={portal}>Manage billing</button>}
              <button className="btn" onClick={signOut}>Sign out</button>
            </div>
          </div>
          {data.access.demo && <div className="demo-banner" style={{ marginTop: 18 }}><b>DEMO ACCESS.</b> You are viewing the premium page without paying. Production would require an active subscription.</div>}
          {notice && <div className="callout info" style={{ marginTop: 14 }}>{notice}</div>}
        </header>
      </div>

      <Section id="provenance" eyebrow="Provenance" title={<>What is Swiss, what is <span className="grad">borrowed.</span></>}
        intro="Every input to this model, and where it comes from. Where a Swiss series does not exist for free, the U.S. one stands in — flagged below and wherever it is used.">
        <Reveal><div className="card">
          <div className="tbl-wrap"><table className="tbl params">
            <thead><tr><th>Input</th><th>Source</th><th>Origin</th></tr></thead>
            <tbody>{data.inputs.map((i) => (
              <tr key={i.label}><td><b style={{ fontWeight: 600 }}>{i.label}</b></td><td>{i.source}</td><td><span className={`tag ${ORIGIN_TAG[i.origin].cls}`}>{ORIGIN_TAG[i.origin].text}</span></td></tr>))}
            </tbody>
          </table></div>
          <div className="callout mt"><b>Why this matters.</b> Swiss and U.S. valuations are not the same thing. The U.S. substitute only decides how many points each warning removes (25, 33 or 40) — it never sells on its own — and the ablation below shows what happens if it is removed.</div>
        </div></Reveal>
      </Section>

      <Section id="rsignal" eyebrow="Today’s signal" title={<>Swiss equity exposure: <span className="grad">{Math.round(s.weight * 100)} %.</span></>}
        intro={<>{s.n_flags} of 3 warnings active at the {monthLabel(s.asof)} close. Each active warning removes {stepPct} points; the step size comes from the <b>U.S.-substituted</b> valuation regime ({regimeLabel(s.regime).toLowerCase()}).</>}>
        <div className="hero-grid" style={{ alignItems: 'start' }}>
          <Reveal><div className="card signal-card">
            <div className="signal-top"><span>Recommended Swiss equity exposure</span><span className="mono">review: end of {monthLabel(s.next_month).split(' ')[0]}</span></div>
            <div className="gauge-wrap"><Gauge value={s.weight} label={`Swiss equity exposure ${Math.round(s.weight * 100)} percent`} />
              <div className="gauge-center"><div className="big">{Math.round(s.weight * 100)}<span style={{ fontSize: 26, color: 'var(--ink-3)' }}>%</span></div><div className="cap">in Swiss equities</div></div></div>
            <div className="signal-rows">
              <div className="sig-row"><span>Warning votes</span><span><b className="mono">{s.n_flags} of 3</b> &nbsp;<Status ok={s.n_flags === 0} okText="All clear" badText="Caution" /></span></div>
              <div className="sig-row"><span>Valuation regime <span className="tag rich" style={{ marginLeft: 6 }}>U.S. substitute</span></span><span className={`tag ${s.regime === 'rich' ? 'rich' : s.regime === 'cheap' ? 'cheap' : 'neutral'}`}>{regimeLabel(s.regime)}</span></div>
              <div className="sig-row"><span>Swiss index vs 10-month average</span><b className="mono">{pct(s.price_vs_sma, 1, true)}</b></div>
            </div>
          </div></Reveal>
          <div className="stack">
            <Flag title="Swiss index vs 10-month average" ok={!s.flags.below_sma} value={pct(s.price_vs_sma, 1, true)} foot={<>Flips if next month’s average falls below <b className="mono">{s.trip_sma.toFixed(1)}</b> ({pct(s.trip_sma_distance, 1)}).</>} />
            <Flag title="12-month momentum vs Swiss cash" ok={!s.flags.neg_mom} value={pct(s.mom12, 1, true)} foot={<>Cash returned {pct(s.cash12, 1)} over 12 months (Swiss rates have been ≈ 0 or negative). Flips if the index falls about <b className="mono">{pct(Math.abs(s.trip_mom_distance), 0)}</b>.</>} />
            <Flag title="Swiss yield curve (10y − short)" ok={!s.flags.curve_inv} value={`${num(s.curve, 2)} pp`} foot={<>10-year {num(s.long_yield, 2)} % vs short rate {num(s.short_rate, 2)} %. Warns when inverted.</>} />
          </div>
        </div>
        <div className="grid g3 mt">
          <Reveal><div className="card ind"><div className="ind-head"><div><h3>CAPE</h3><div className="sub">U.S. Shiller CAPE — not Swiss</div></div><span className="tag rich">U.S. substitute</span></div>
            <div className="value">{num(s.us_cape, 1)}<small>{Math.round(s.us_cape_pct * 100)}th percentile</small></div>
            <Sparkline values={data.series.us_cape} label="U.S. CAPE (substitute)" color="var(--s4)" />
          </div></Reveal>
          <Reveal><div className="card ind"><div className="ind-head"><div><h3>Buffett indicator</h3><div className="sub">U.S. equity ÷ GDP — not Swiss</div></div><span className="tag rich">U.S. substitute</span></div>
            <div className="value">{pct(s.us_buffett, 0)}<small>{Math.round(s.us_buffett_pct * 100)}th percentile</small></div>
            <Sparkline values={data.series.us_buffett} label="U.S. Buffett indicator (substitute)" color="var(--s4)" />
          </div></Reveal>
          <Reveal><div className="card ind"><div className="ind-head"><div><h3>Regime</h3><div className="sub">Average of the two U.S. percentiles</div></div><span className={`tag ${s.regime === 'rich' ? 'rich' : 'neutral'}`}>{regimeLabel(s.regime)}</span></div>
            <div className="value">{Math.round(s.val_score * 100)}<small>/ 100</small></div>
            <div className="foot">A Swiss-native valuation would be better. Until a free source exists, treat the regime as a U.S.-global-cycle proxy, not a verdict on Swiss stocks.</div>
          </div></Reveal>
        </div>
      </Section>

      <Section id="rkpi" eyebrow="Track record" title={<>How the rules would have done <span className="grad">in Switzerland.</span></>}
        intro="Same rules, same parameters, same costs and timing as the U.S. model. Nothing was re-tuned for Switzerland.">
        <div className="range-row">
          <div className="sub" style={{ color: 'var(--ink-3)' }}>{P.months} months, CHF, dividends assumed {pct(data.dividend_yield, 1)} a year, 0.10 % cost per trade. Hypothetical backtest.</div>
          <div className="seg" role="group" aria-label="Period">
            {(['full', 'since1990', 'since2010', 'lost_decades'] as const).map((k) => <button key={k} aria-pressed={pk === k} onClick={() => setPk(k)}>{sinceFirst(k)}</button>)}
          </div>
        </div>
        <div className="grid g4 kpis">
          <K win={b.max_dd > h.max_dd} label="Worst drawdown" main={pct(b.max_dd, 1)} vs={pct(h.max_dd, 1)} note={`Swiss buy & hold lost ${pct(Math.abs(h.max_dd), 0)} at the worst point.`} />
          <K win={b.cagr >= h.cagr} label="Annual return (CAGR)" main={pct(b.cagr, 1)} vs={pct(h.cagr, 1)} note={b.cagr >= h.cagr ? 'Upside preserved in this window.' : `Gives up ${pct(h.cagr - b.cagr, 1)} a year here.`} />
          <K win={(b.sharpe ?? 0) > (h.sharpe ?? 0)} label="Sharpe ratio" main={num(b.sharpe)} vs={num(h.sharpe)} note="Return per unit of volatility, over Swiss cash." />
          <K win={b.down_capture < b.up_capture} label="Up / down capture" main={`${Math.round(b.up_capture * 100)} / ${Math.round(b.down_capture * 100)}`} vs="100 / 100" note="Share of up-month gains vs down-month losses taken." />
        </div>
      </Section>

      <Performance id="rperformance" eyebrow="Swiss performance" model={data} series={data.series} starts={starts} defaultStart={Number(first)}
        title={<>A smoother road, <span className="grad">a slower climb.</span></>}
        intro="Drag across any chart — all three stay in sync. Pick a start year and the statistics recompute."
        source={<>Source: Swiss share-price index (OECD via FRED, monthly average, price only) plus an assumed {pct(data.dividend_yield, 1)} dividend yield; Swiss short rates as cash; </>} />

      <Crashes id="rcrashes" model={data} names={CH_NAMES}
        intro="Swiss declines of 15 % or more, judged over identical windows for every strategy."
        callouts={<div className="grid g2 mt">
          <div className="callout good"><b>Where it helped:</b> the long bears — 1989–91, the dot-com bust and the financial crisis — where Bulwark’s worst loss was roughly −7 % to −21 % against −25 % to −48 % for Swiss buy &amp; hold.</div>
          <div className="callout"><b>Where it didn’t:</b> sudden shocks — 1987, 1998 and COVID-2020 — fell too fast for a monthly rule, and the model gave back some of the rebound. As in the U.S., it limits how long a bear can hurt; it doesn’t predict one.</div>
        </div>} />

      <Section id="rreality" eyebrow="Reality check" title={<>The honest summary for <span className="grad">Switzerland.</span></>}
        intro="A regional model is only worth paying for if it tells you the truth about your market, including when the edge is thin.">
        <div className="grid g2">
          <Reveal><div className="card">
            <h3>What the numbers say</h3>
            <ul className="clean" style={{ marginTop: 14 }}>
              <li><b>Risk:</b> worst drawdown {pct(m.bulwark.max_dd, 0)} vs {pct(m.buyhold.max_dd, 0)}; Sharpe {num(m.bulwark.sharpe)} vs {num(m.buyhold.sharpe)}.</li>
              <li><b>Return:</b> {pct(m.bulwark.cagr, 1)} vs {pct(m.buyhold.cagr, 1)} a year — {diff > 0 ? <>about <b>{pct(diff, 1)} a year less</b> than buy &amp; hold</> : 'no shortfall'}. The U.S. model gave up nothing over its full sample. Swiss cash also earned very little for much of this period, so time spent waiting in cash pays less.</li>
              <li><b>Statistical confidence</b> (block bootstrap): drawdown better in {pct(data.bootstrap.p_maxdd_better, 0)} of resamples, Sharpe better in {pct(data.bootstrap.p_sharpe_better, 0)}, return within 1 pt in {pct(data.bootstrap.p_cagr_within_1pt, 0)}.</li>
              <li><b>Rolling 10 years:</b> ahead of buy &amp; hold in {pct(data.rolling10.share_bulwark_ahead, 0)} of windows; worst 10 years {pct(data.rolling10.worst_bulwark, 1, true)} vs {pct(data.rolling10.worst_buyhold, 1, true)} a year.</li>
            </ul>
          </div></Reveal>
          <Reveal><div className="card">
            <h3>Fragile spots</h3>
            <ul className="clean" style={{ marginTop: 14 }}>
              <li><b>Dividend assumption.</b> There is no free Swiss total-return index, so a {pct(data.dividend_yield, 1)} yield is assumed. The table shows 0 % and 3.5 %.</li>
              <li><b>U.S. valuation substitute.</b> Removing it changes little (see the table), which also means Swiss valuation isn’t adding much here.</li>
              <li><b>Short rates.</b> Swiss call-money (to 1999) is spliced to 3-month interbank rates; different instruments.</li>
              <li><b>Averaged prices.</b> Monthly averages understate drawdowns for both strategy and benchmark.</li>
            </ul>
          </div></Reveal>
        </div>
        <Reveal><div className="card mt">
          <h3>Ablations &amp; assumption sensitivity</h3>
          <div className="sub" style={{ marginBottom: 14 }}>{first} – today, same data and costs for every row.</div>
          <div className="tbl-wrap"><table className="tbl">
            <thead><tr><th>Variant</th><th>CAGR</th><th>Swiss buy &amp; hold</th><th>Worst DD</th><th>Sharpe</th></tr></thead>
            <tbody>{ab.map((a, i) => (
              <tr key={a.name} className={i === 0 ? 'hl' : ''}><td>{a.name}</td><td>{pct(a.full.cagr)}</td><td>{a.full.bh_cagr != null ? pct(a.full.bh_cagr) : '–'}</td><td>{pct(a.full.max_dd)}</td><td>{num(a.full.sharpe)}</td></tr>))}
            </tbody>
          </table></div>
        </div></Reveal>
      </Section>

      <footer className="footer"><div className="wrap">
        <p><b style={{ color: 'var(--ink-2)' }}>Bulwark Premium · Switzerland</b> · data through {monthLabel(s.asof)} · generated {data.generated} · leak audit: {data.audit.summary}</p>
        <p>Research and education only, not investment advice. Hypothetical results with the benefit of hindsight; past performance does not guarantee future results. U.S. series are used as labelled substitutes where no Swiss data exist.</p>
      </div></footer>
    </>
  )
}

function Flag({ title, ok, value, foot }: { title: string; ok: boolean; value: string; foot: React.ReactNode }) {
  return <Reveal><div className="card ind" style={{ gap: 10 }}>
    <div className="ind-head"><h3>{title}</h3><Status ok={ok} /></div>
    <div className="value" style={{ fontSize: 26 }}>{value}</div>
    <div className="foot">{foot}</div>
  </div></Reveal>
}

function K({ label, main, vs, note, win }: { label: string; main: string; vs: string; note: string; win: boolean }) {
  return <div className={`card kpi ${win ? 'win' : ''}`}><div className="label">{label}</div><div className="vals"><span className="main">{main}</span><span className="vs">vs <i>{vs}</i></span></div><div className="note">{note}</div></div>
}
