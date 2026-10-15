import type { Model, Series } from '../types'
import { Sparkline } from '../charts/Sparkline'
import { monthLabel, pct, num, regimeLabel } from '../format'
import { Reveal, Section, Status } from './ui'

const ordinal = (p: number) => {
  const n = Math.round(p * 100)
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`
}

export function SignalBoard({ model, series }: { model: Model; series: Series }) {
  const s = model.snapshot
  const since = series.d.findIndex((d) => d >= '1970-01')
  const tail = (a: (number | null)[]) => a.slice(since)
  const stepPct = Math.round(s.step * 100)

  return (
    <Section id="signal" eyebrow="Today’s signal"
      title={<>Three warnings can cut exposure. <span className="grad">Valuation decides how hard.</span></>}
      intro={<>Updated for the {monthLabel(s.asof)} close. Each check is a single, widely known rule. Equity exposure is 100 % minus {stepPct} points for every active warning — and the “{regimeLabel(s.regime).toLowerCase()}” regime sets that step size.</>}>

      <div className="eyebrow" style={{ marginBottom: 14 }}>Warning votes · these cut equity</div>
      <div className="grid g3">
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>Price vs 10-month average</h3><div className="sub">Faber (2007) trend rule</div></div><Status ok={!s.flags.below_sma} /></div>
          <div className="value">{pct(s.price_vs_sma, 1, true)}<small>S&amp;P {Math.round(s.price).toLocaleString()} vs avg {Math.round(s.sma).toLocaleString()}</small></div>
          <Gap fraction={Math.min(1, Math.abs(s.trip_sma_distance) / 0.2)} />
          <div className="foot">Flips if next month’s average S&amp;P falls below <b className="mono">{Math.round(s.trip_sma).toLocaleString()}</b> ({pct(s.trip_sma_distance, 1)}).</div>
        </div></Reveal>
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>12-month momentum</h3><div className="sub">Time-series momentum vs cash</div></div><Status ok={!s.flags.neg_mom} /></div>
          <div className="value">{pct(s.mom12, 1, true)}<small>vs T-bills {pct(s.cash12, 1)}</small></div>
          <Gap fraction={Math.min(1, Math.abs(s.trip_mom_distance) / 0.25)} />
          <div className="foot">Flips if the index falls about <b className="mono">{pct(Math.abs(s.trip_mom_distance), 0)}</b> from here (12-month return below cash).</div>
        </div></Reveal>
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>Yield curve (10y − 3m)</h3><div className="sub">Inversion has preceded recessions</div></div><Status ok={!s.flags.curve_inv} /></div>
          <div className="value">{num(s.curve, 2)}<small>percentage points</small></div>
          <Gap fraction={Math.min(1, s.curve / 3)} />
          <div className="foot">Warns when the curve inverts (below 0). It has been {s.curve >= 0 ? 'positively sloped' : 'inverted'} for the latest reading.</div>
        </div></Reveal>
      </div>

      <div className="eyebrow" style={{ margin: '34px 0 14px' }}>Valuation · sets the step size, never a sell signal on its own</div>
      <div className="grid g3">
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>CAPE (Shiller P/E10)</h3><div className="sub">Point-in-time, earnings lagged 3 months</div></div><span className="tag rich">{ordinal(s.cape_pct)} percentile</span></div>
          <div className="value">{num(s.cape, 1)}<small>history median {num(s.cape_median, 1)}</small></div>
          <Sparkline values={tail(series.cape)} refValue={s.cape_median} label="CAPE since 1970" color="var(--s4)" />
          <div className="foot">Higher than {Math.round(s.cape_pct * 100)} % of all readings known at the time. Published CAPE: {num(s.cape_shiller, 1)}.</div>
        </div></Reveal>
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>Buffett indicator</h3><div className="sub">U.S. corporate equity ÷ GDP (Fed Z.1)</div></div><span className="tag rich">{ordinal(s.buffett_pct)} percentile</span></div>
          <div className="value">{pct(s.buffett, 0)}<small>history median {pct(s.buffett_median, 0)}</small></div>
          <Sparkline values={tail(series.buffett)} refValue={s.buffett_median} label="Buffett indicator since 1970" color="var(--s4)" />
          <div className="foot">Nowcast between quarterly Fed releases using the S&amp;P 500 move; GDP lagged as published.</div>
        </div></Reveal>
        <Reveal><div className="card ind">
          <div className="ind-head"><div><h3>Regime</h3><div className="sub">Average of the two percentiles</div></div><span className={`tag ${s.regime === 'rich' ? 'rich' : s.regime === 'cheap' ? 'cheap' : 'neutral'}`}>{regimeLabel(s.regime)}</span></div>
          <div className="value">{Math.round(s.val_score * 100)}<small>/ 100 valuation score</small></div>
          <div>
            <div className="bar"><i style={{ width: `${s.val_score * 100}%` }} /><u style={{ left: '50%' }} /><u style={{ left: '80%' }} /></div>
            <div className="bar-labels"><span>cheap</span><span>median 50</span><span>rich ≥ 80</span></div>
          </div>
          <div className="foot">Rich markets fall harder, so each warning removes {stepPct} points instead of 33. Valuation alone never sells.</div>
        </div></Reveal>
      </div>

      <div className="eyebrow" style={{ margin: '34px 0 14px' }}>Context · shown for awareness, deliberately <u style={{ textDecorationStyle: 'dotted' }}>not</u> used to cut equity</div>
      <div className="grid g4">
        <Ctx title="Credit spread (Baa − 10y)" value={`${num(s.credit_spread, 2)} pp`} note={`${ordinal(s.credit_pct)} percentile of history`} />
        <Ctx title="Sahm recession gap" value={s.sahm_gap == null ? '–' : `${num(s.sahm_gap, 2)} pp`} note={`Rule triggers at +0.50 · ${s.flags.sahm ? 'TRIGGERED' : 'not triggered'}`} />
        <Ctx title="VIX" value={s.live.vix != null ? num(s.live.vix, 1) : '–'} note={s.live.vix_date ? `Close ${s.live.vix_date}` : ''} />
        <Ctx title="Chicago Fed NFCI" value={s.live.nfci != null ? num(s.live.nfci, 2) : '–'} note={s.live.nfci_date ? `Below 0 = looser than average · ${s.live.nfci_date}` : ''} />
      </div>
      <div className="callout info mt"><b>Why context-only?</b> Credit stress and the Sahm rule are <i>lagging</i>: in both 1970–2026 and the 1940–69 holdout, stocks earned <i>more</i> than average in the months after they fired, because they trip near bottoms. Using them to sell would have cost upside. The evidence table below shows it.</div>

      <div className="how">
        <Reveal><div className="card">
          <h3>How the equity weight is computed</h3>
          <div className="sub" style={{ marginBottom: 14 }}>Equity % = 100 % − step × active warnings (min 0). Cash = 3-month T-bills. Rebalanced monthly at the close.</div>
          <table className="mat">
            <thead><tr><th></th>{[0, 1, 2, 3].map((n) => <th key={n}>{n} warning{n === 1 ? '' : 's'}</th>)}</tr></thead>
            <tbody>
              {(['cheap', 'fair', 'rich'] as const).map((r) => {
                const step = Number(r === 'cheap' ? model.params.step_cheap : r === 'fair' ? model.params.step_fair : model.params.step_rich)
                return (
                  <tr key={r}>
                    <td className="rowh">{r === 'cheap' ? 'Below-median valuation' : r === 'fair' ? 'Fair' : 'Rich (top 20 %)'}</td>
                    {[0, 1, 2, 3].map((n) => {
                      const w = Math.max(0, 1 - step * n)
                      const cur = r === s.regime && n === s.n_flags
                      return <td key={n} className={cur ? 'cur' : ''} style={{ background: `color-mix(in srgb, var(--s1) ${Math.round(w * 78)}%, var(--surface-3))`, color: w > 0.5 ? '#fff' : 'var(--ink)' }}>{Math.round(w * 100)}%</td>
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div></Reveal>
        <Reveal><div className="card">
          <h3>What would change the call?</h3>
          <ul className="clean mt" style={{ marginTop: 14 }}>
            <li><b>Trend break.</b> A month averaging below {Math.round(s.trip_sma).toLocaleString()} adds one warning → exposure {Math.round(Math.max(0, 1 - s.step) * 100)} %.</li>
            <li><b>Momentum fades.</b> If the 12-month return drops below cash, a second warning → {Math.round(Math.max(0, 1 - 2 * s.step) * 100)} %.</li>
            <li><b>Curve inverts.</b> Adds a third → {Math.round(Math.max(0, 1 - 3 * s.step) * 100)} %. Everything clears → back to 100 %.</li>
          </ul>
          <p className="sub" style={{ marginTop: 14 }}>Valuation is at the extreme top of its history. The model does not call a top — it simply cuts harder once the tape agrees.</p>
        </div></Reveal>
      </div>
    </Section>
  )
}

function Gap({ fraction }: { fraction: number }) {
  return (
    <div>
      <div className="bar"><i style={{ width: `${Math.max(4, fraction * 100)}%` }} /></div>
      <div className="bar-labels"><span>at trigger</span><span>buffer →</span></div>
    </div>
  )
}

function Ctx({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <Reveal><div className="card ind" style={{ gap: 10 }}>
      <div className="ind-head"><h3 style={{ fontSize: 14 }}>{title}</h3><span className="ctx-tag">context</span></div>
      <div className="value" style={{ fontSize: 26 }}>{value}</div>
      <div className="foot">{note}</div>
    </div></Reveal>
  )
}
