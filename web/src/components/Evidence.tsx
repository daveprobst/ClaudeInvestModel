import type { ReactNode } from 'react'
import type { Model, Variant } from '../types'
import { num, pct } from '../format'
import { Icon, Reveal, Section } from './ui'

export function Evidence({ model }: { model: Model }) {
  const hf = model.headline.full.metrics, hh = model.headline.holdout.metrics
  const bs = model.bootstrap
  const au = model.audit
  return (
    <Section id="evidence" eyebrow="Is it overfit?"
      title={<>Built to survive <span className="grad">contact with the future.</span></>}
      intro="Most backtests are stories told after seeing the ending. Bulwark’s rules were fixed from textbook conventions, then tested in ways that give overfitting nowhere to hide — and every shortcoming is on this page too.">
      <div className="principles">
        <Principle icon={Icon.lock} title="No fitted numbers" text="10-month average, 12-month momentum, quintiles, 0 on the yield curve. Round conventions that predate the model — nothing swept or optimised to maximise the backtest." />
        <Principle icon={Icon.clock} title="Point-in-time data" text="Earnings lag 3 months, Fed equity & GDP lag 3, jobs data 1. Valuation percentiles use only the past (expanding window). No level was calibrated to a known peak." />
        <Principle icon={Icon.shield} title={au.passed ? 'Leak audit passes' : 'Leak audit'} text={`Every signal is recomputed from data truncated at ${27} random dates and must match exactly; a mutation test confirms the audit catches an injected leak. ${au.summary}.`} />
        <Principle icon={Icon.globe} title="Out-of-sample checks" text="A pre-1970 holdout and eight stock-market indices (seven foreign) the rules were never designed on — plus a block bootstrap on the full record." />
      </div>

      <div className="split mt2">
        <Reveal><div className="card">
          <h3>The 1940 – 1969 holdout</h3>
          <div className="sub" style={{ marginBottom: 14 }}>Same rules, an era the design never looked at. Valuation leans on CAPE alone until enough Buffett-indicator history exists (mid-1960s).</div>
          <div className="tbl-wrap"><table className="tbl">
            <thead><tr><th></th><th>CAGR</th><th>Worst DD</th><th>Sharpe</th></tr></thead>
            <tbody>
              <tr className="hl"><td>Bulwark</td><td>{pct(hh.bulwark.cagr)}</td><td>{pct(hh.bulwark.max_dd)}</td><td>{num(hh.bulwark.sharpe)}</td></tr>
              <tr><td>Buy &amp; hold</td><td>{pct(hh.buyhold.cagr)}</td><td>{pct(hh.buyhold.max_dd)}</td><td>{num(hh.buyhold.sharpe)}</td></tr>
              <tr><td>Static mix, same avg. equity</td><td>{pct(hh.static.cagr)}</td><td>{pct(hh.static.max_dd)}</td><td>{num(hh.static.sharpe)}</td></tr>
              <tr><td>10-month rule only</td><td>{pct(hh.faber.cagr)}</td><td>{pct(hh.faber.max_dd)}</td><td>{num(hh.faber.sharpe)}</td></tr>
            </tbody>
          </table></div>
          <p className="sub" style={{ marginTop: 12 }}>Holdout verdict: drawdown cut by a third and a better Sharpe, but {pct(hh.buyhold.cagr - hh.bulwark.cagr, 1)} a year less return in a market that mostly went up. Full-sample (1970+): {pct(hf.bulwark.cagr)} vs {pct(hf.buyhold.cagr)}.</p>
        </div></Reveal>

        <Reveal><div className="card">
          <h3>Could it just be luck?</h3>
          <div className="sub" style={{ marginBottom: 14 }}>{bs.draws.toLocaleString()} block-bootstrap resamples of 1970–2026 ({bs.block_months}-month blocks keep trends intact)</div>
          <div className="stack" style={{ gap: 12 }}>
            <Prob label="Sharpe ratio beats buy & hold" p={bs.p_sharpe_better} />
            <Prob label="Worst drawdown is smaller" p={bs.p_maxdd_better} />
            <Prob label="Return within 1 pt/yr of buy & hold (or better)" p={bs.p_cagr_within_1pt} />
          </div>
          <p className="sub" style={{ marginTop: 14 }}>90 % range for the annual-return difference: <b className="mono">{pct(bs.cagr_diff_q[0], 1, true)}</b> to <b className="mono">{pct(bs.cagr_diff_q[2], 1, true)}</b>. Read: return is statistically a coin-flip vs buy &amp; hold; the <i>risk reduction</i> is the robust part.</p>
        </div></Reveal>
      </div>

      <Reveal><div className="card mt">
        <h3>Does each ingredient earn its keep?</h3>
        <div className="sub" style={{ marginBottom: 14 }}>Ablations — every variant uses the same data, costs and timing. Highlighted = the final model.</div>
        <div className="tbl-wrap"><table className="tbl">
          <thead><tr><th>Variant</th><th>CAGR</th><th>Worst DD</th><th>Sharpe</th><th>Up cap.</th><th>Down cap.</th><th>Holdout CAGR</th><th>Holdout DD</th></tr></thead>
          <tbody>{model.ablations.map((a, i) => (
            <tr key={a.name} className={i === 0 ? 'hl' : ''}>
              <td>{a.name}</td><td>{pct(a.full.cagr)}</td><td>{pct(a.full.max_dd)}</td><td>{num(a.full.sharpe)}</td><td>{pct(a.full.up, 0)}</td><td>{pct(a.full.down, 0)}</td><td>{pct(a.holdout.cagr)}</td><td>{pct(a.holdout.max_dd)}</td>
            </tr>))}</tbody>
        </table></div>
        <div className="grid g2 mt">
          <div className="callout info"><b>Honest take.</b> The lone 10-month rule is a very strong baseline — shallower drawdowns than Bulwark. What layering adds is <i>graded</i> exposure (less cliff-edge trading, about 7 pts more upside capture) and diversification across independent warning types instead of betting everything on one rule.</div>
          <div className="callout"><b>A change I made, and why.</b> The first draft also cut equity on credit spreads and the Sahm rule. Diagnostics showed they fire <i>after</i> the damage — and the holdout agreed — so they were demoted to context (row “v0 – rejected”: lower return, deeper drawdown). Every variant tried is listed here.</div>
        </div>
      </div></Reveal>

      <div className="split mt">
        <Reveal><div className="card">
          <h3>What each warning actually knows</h3>
          <div className="sub" style={{ marginBottom: 14 }}>Average annual S&amp;P excess return over cash in the month <i>after</i> the flag was on vs off</div>
          <FlagBars model={model} />
        </div></Reveal>
        <Reveal><div className="card">
          <h3>Eight stock markets, trend rule only</h3>
          <div className="sub" style={{ marginBottom: 14 }}>Price indices since 1960, cash earns 0 % (pessimistic). Worst drawdown: buy &amp; hold vs trend votes</div>
          <div className="tbl-wrap"><table className="tbl">
            <thead><tr><th>Market</th><th>B&amp;H DD</th><th>Trend DD</th><th>B&amp;H CAGR</th><th>Trend CAGR</th></tr></thead>
            <tbody>{model.international.map((r) => (
              <tr key={r.market}><td>{r.market}</td><td>{pct(r.bh_dd, 0)}</td><td className={r.trend_dd > r.bh_dd ? 'pos' : 'neg'}>{pct(r.trend_dd, 0)}</td><td>{pct(r.bh_cagr)}</td><td>{pct(r.trend_cagr)}</td></tr>))}</tbody>
          </table></div>
          <p className="sub" style={{ marginTop: 12 }}>Drawdown shrank in {model.international.filter((r) => r.trend_dd > r.bh_dd).length} of {model.international.length} markets; annual return was within about ±1.5 points in 7 of 8. (Seven are foreign; valuation data don’t exist for them, so only the trend pillar is tested.)</p>
        </div></Reveal>
      </div>

      <div className="eyebrow" style={{ margin: '40px 0 14px' }}>Sensitivity — nudge the pre-set numbers, results barely move</div>
      <div className="grid g2">
        <Reveal><div className="card">
          <h3>Look-back lengths</h3>
          <div className="sub" style={{ marginBottom: 12 }}>Worst drawdown by moving-average months (rows) × momentum months (columns). Outlined = chosen (10, 12).</div>
          <Heat rows={[6, 8, 10, 12]} cols={[6, 9, 12]} rowLabel="SMA" colLabel="mom" cell={(r, c) => model.sensitivity.lookbacks.find((x) => x.sma === r && x.mom === c)} metric="max_dd" />
          <p className="sub" style={{ marginTop: 10 }}>Worst drawdown ranges {pct(Math.max(...model.sensitivity.lookbacks.map((x) => x.max_dd)), 0)} to {pct(Math.min(...model.sensitivity.lookbacks.map((x) => x.max_dd)), 0)}; CAGR {pct(Math.min(...model.sensitivity.lookbacks.map((x) => x.cagr)))} to {pct(Math.max(...model.sensitivity.lookbacks.map((x) => x.cagr)))} across all 12 (buy &amp; hold: {pct(hf.buyhold.max_dd, 0)}, {pct(hf.buyhold.cagr)}).</p>
        </div></Reveal>
        <Reveal><div className="card">
          <h3>Valuation thresholds</h3>
          <div className="sub" style={{ marginBottom: 12 }}>CAGR by “rich” percentile (rows) × “cheap” percentile (columns). Outlined = chosen (80 %, 50 %).</div>
          <Heat rows={[0.7, 0.8, 0.9]} cols={[0.4, 0.5, 0.6]} rowLabel="rich" colLabel="cheap" fmtKey={(v) => `${Math.round(v * 100)}`} cell={(r, c) => model.sensitivity.valuation.find((x) => x.rich === r && x.cheap === c)} metric="cagr" />
          <p className="sub" style={{ marginTop: 10 }}>CAGR {pct(Math.min(...model.sensitivity.valuation.map((x) => x.cagr)))} to {pct(Math.max(...model.sensitivity.valuation.map((x) => x.cagr)))}; worst drawdown stays within {pct(Math.max(...model.sensitivity.valuation.map((x) => x.max_dd)), 0)} to {pct(Math.min(...model.sensitivity.valuation.map((x) => x.max_dd)), 0)}.</p>
        </div></Reveal>
      </div>
      <Reveal><div className="card mt">
        <h3>Frictions, timing, defensive asset, start date</h3>
        <div className="sub" style={{ marginBottom: 14 }}>Same model, one assumption changed at a time.</div>
        <div className="tbl-wrap"><table className="tbl">
          <thead><tr><th>Assumption</th><th>Setting</th><th>CAGR</th><th>Worst DD</th><th>Sharpe</th></tr></thead>
          <tbody>{model.sensitivity.other.map((r, i) => (
            <tr key={i} className={r.chosen ? 'hl' : ''}><td>{r.group}</td><td style={{ fontFamily: 'var(--sans)' }}>{r.label}</td><td>{pct(r.cagr)}</td><td>{pct(r.max_dd)}</td><td>{num(r.sharpe)}</td></tr>))}</tbody>
        </table></div>
      </div></Reveal>
    </Section>
  )
}

function Principle({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <Reveal><div className="card principle"><div className="ico">{icon}</div><h3>{title}</h3><p>{text}</p></div></Reveal>
}

function Prob({ label, p }: { label: string; p: number }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 6 }}><span style={{ color: 'var(--ink-2)' }}>{label}</span><b className="mono">{Math.round(p * 100)}%</b></div>
      <div className="bar"><i style={{ width: `${p * 100}%` }} /></div>
    </div>
  )
}

const FLAG_NAMES: Record<string, string> = { below_sma: 'Below 10-month avg', neg_mom: 'Negative 12M momentum', curve_inv: 'Yield curve inverted', credit_stress: 'Credit spreads top quintile', sahm: 'Sahm rule triggered' }
function FlagBars({ model }: { model: Model }) {
  const flags = ['below_sma', 'neg_mom', 'curve_inv', 'credit_stress', 'sahm']
  const rows = model.flag_diagnostics.filter((r) => r.period.startsWith('1970'))
  const hold = model.flag_diagnostics.filter((r) => r.period.startsWith('1940'))
  const max = 16
  return (
    <div className="stack" style={{ gap: 14 }}>
      {flags.map((f) => {
        const a = rows.find((r) => r.flag === f), b = hold.find((r) => r.flag === f)
        const cut = ['below_sma', 'neg_mom', 'curve_inv'].includes(f)
        return (
          <div key={f}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5, marginBottom: 5 }}>
              <b style={{ fontWeight: 600 }}>{FLAG_NAMES[f]}</b>
              <span className={`tag ${cut ? 'ok' : 'neutral'}`} style={{ fontSize: 11.5 }}>{cut ? 'cuts equity' : 'context only'}</span>
            </div>
            <Pair label="ON" v={a?.xs_on} color={cut ? 'var(--crit)' : 'var(--s2)'} max={max} />
            <Pair label="OFF" v={a?.xs_off} color="var(--s1)" max={max} />
            {b && b.xs_on != null && <div className="sub" style={{ fontSize: 12, marginTop: 3 }}>Holdout 1940–69: ON {num(b.xs_on, 1)}% · OFF {num(b.xs_off, 1)}%</div>}
          </div>
        )
      })}
      <p className="sub">Bars: 1970–2026, % per year. A useful sell signal has a <i>low</i> bar when ON. Credit &amp; Sahm show the opposite. Caveat: 12-month momentum was also wrong-way in the 1940–69 holdout (shown above) — it is the weakest single rule and a candidate for removal.</p>
    </div>
  )
}
function Pair({ label, v, color, max }: { label: string; v: number | null | undefined; color: string; max: number }) {
  return (
    <div className="hbar" style={{ gridTemplateColumns: '34px 1fr 52px', marginBottom: 4 }}>
      <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{label}</span>
      <div className="track" style={{ height: 8 }}><div className="fill" style={{ width: v == null ? 0 : `${Math.max(1, Math.min(100, (Math.max(v, 0) / max) * 100))}%`, background: color }} /></div>
      <b style={{ fontSize: 12.5 }}>{v == null ? '–' : `${num(v, 1)}%`}</b>
    </div>
  )
}

function Heat<T extends Variant>({ rows, cols, rowLabel, colLabel, cell, metric, fmtKey }: {
  rows: number[]; cols: number[]; rowLabel: string; colLabel: string; metric: 'cagr' | 'max_dd'
  cell: (r: number, c: number) => (T & { chosen: boolean }) | undefined; fmtKey?: (v: number) => string
}) {
  const vals = rows.flatMap((r) => cols.map((c) => cell(r, c)?.[metric] ?? 0))
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const k = fmtKey ?? ((v: number) => String(v))
  return (
    <div className="heat" style={{ gridTemplateColumns: `54px repeat(${cols.length}, 1fr)` }}>
      <div className="heat-axis">{rowLabel}↓ {colLabel}→</div>
      {cols.map((c) => <div key={c} className="heat-axis">{k(c)}</div>)}
      {rows.map((r) => (
        <Row key={r} r={r} cols={cols} cell={cell} lo={lo} hi={hi} metric={metric} k={k} />
      ))}
    </div>
  )
}
function Row<T extends Variant>({ r, cols, cell, lo, hi, metric, k }: { r: number; cols: number[]; cell: (r: number, c: number) => (T & { chosen: boolean }) | undefined; lo: number; hi: number; metric: 'cagr' | 'max_dd'; k: (v: number) => string }) {
  return (
    <>
      <div className="heat-axis">{k(r)}</div>
      {cols.map((c) => {
        const x = cell(r, c)
        const v = x?.[metric] ?? 0
        const t = hi === lo ? 0.5 : (v - lo) / (hi - lo)       // higher = better for both metrics
        return (
          <div key={c} className={`heat-cell ${x?.chosen ? 'chosen' : ''}`} style={{ background: `color-mix(in srgb, var(--seq-400) ${Math.round(18 + t * 62)}%, var(--surface-3))`, color: t > 0.45 ? '#fff' : 'var(--ink)' }} title={x ? `CAGR ${pct(x.cagr)}, worst DD ${pct(x.max_dd)}, Sharpe ${num(x.sharpe)}` : ''}>
            {pct(v, metric === 'cagr' ? 1 : 0)}
            <small>Sharpe {num(x?.sharpe)}</small>
          </div>
        )
      })}
    </>
  )
}
