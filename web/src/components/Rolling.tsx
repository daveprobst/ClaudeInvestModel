import { useEffect, useState } from 'react'
import { pct, num, regimeLabel } from '../format'
import { Gauge } from '../charts/Gauge'
import { Section, Status } from './ui'

type Stats = { cagr: number; max_dd: number; sharpe: number | null; final_multiple: number }
type RollingData = {
  version: string; generated: string; asof: string; instrument: string
  snapshot: { price: number; fast: number; slow: number; momentum: number; cash12: number; curve: number; weight: number; warnings: number; regime: string; valuation_asof: string; flags: Record<string, boolean> }
  backtest: { start: string; end: string; sessions: number; strategy: Stats; buyhold: Stats; avg_equity: number; trades: number; dates: string[]; strategy_curve: number[]; buyhold_curve: number[] }
  sources: { name: string; url: string; asof: string }[]
}

export function Rolling() {
  const [data, setData] = useState<RollingData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    const refresh = () => fetch(`${import.meta.env.BASE_URL}data/rolling.json`, { signal: controller.signal, cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error(`Data request failed (${r.status})`); return r.json() as Promise<RollingData> })
      .then(d => { setData(d); setError('') })
      .catch(e => { if (e.name !== 'AbortError') setError(String(e)) })
    void refresh()
    const timer = window.setInterval(() => { void refresh() }, 15 * 60 * 1000)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [])
  if (!data) return <div className="skeleton" role="status">{error || 'Loading rolling daily model…'}</div>
  const s = data.snapshot, b = data.backtest
  const stale = Date.now() - Date.parse(`${data.asof}T21:00:00Z`) > 5 * 86400000
  return <>
    <header className="hero"><div className="wrap">
      <div className="hero-grid"><div>
        <span className="pill"><i className="dot" /> Rolling daily · completed session {data.asof}</span>
        <h1>A monthly lens.<br /><span className="grad">A fresh reading each day.</span></h1>
        <p className="lead">Bulwark’s daily variant smooths the latest 21 trading sessions and compares them with a 210-session trend. It checks 12-month momentum and the yield curve each day. Valuation uses the latest completed-month model.</p>
        <p className="sub">{data.instrument} · closing prices, not intraday quotes · next review after a new completed session is available.</p>
        <div className="hero-cta"><a className="btn primary" href="#signal">Current warnings →</a><a className="btn" href="#performance">Recalculated performance</a></div>
      </div><div className="card signal-card" aria-label="Rolling daily allocation signal">
        <div className="signal-top"><span>Rolling model equity allocation</span><span className="mono">{data.asof}</span></div>
        <div className="gauge-wrap"><Gauge value={s.weight} label={`Rolling equity allocation ${Math.round(s.weight * 100)} percent`} /><div className="gauge-center"><div className="big">{Math.round(s.weight * 100)}<span style={{ fontSize: 26 }}>%</span></div><div className="cap">in equities</div></div></div>
        <div className="signal-rows"><div className="sig-row"><span>Warnings</span><b>{s.warnings} of 3</b></div><div className="sig-row"><span>Valuation</span><b>{regimeLabel(s.regime)}</b></div><div className="sig-row"><span>Valuation observation</span><b>{s.valuation_asof}</b></div></div>
      </div></div>
      {(stale || error) && <p role="alert" className="callout">{error || `Price data is older than five calendar days. Last completed observation: ${data.asof}.`} The displayed signal retains its observation date.</p>}
    </div></header>
    <Section id="signal" eyebrow="Rolling daily signal" title="Three warnings, checked daily." intro={<>Each warning removes {Math.round((1 - Math.max(0, 1 - (s.regime === 'rich' ? .4 : s.regime === 'cheap' ? .25 : 1 / 3))) * 100)} percentage points of equity allocation. Latest SPY close: ${num(s.price)} on {data.asof}.</>}>
      <div className="grid g3">
        <Signal title="Rolling trend" warning={s.flags.trend_warning} value={pct(s.fast / s.slow - 1, 2, true)} detail={`21-session average $${num(s.fast)} vs 210-session average $${num(s.slow)}. Warns when the shorter average is below the longer one.`} />
        <Signal title="12-month momentum" warning={s.flags.momentum_warning} value={pct(s.momentum, 2)} detail={`21-session average dividend-adjusted price versus the same window 252 sessions earlier. Cash hurdle ${pct(s.cash12, 2)}.`} />
        <Signal title="Yield curve" warning={s.flags.curve_warning} value={`${num(s.curve)} pp`} detail="Prior-session Treasury 10-year yield minus 3-month T-bill rate. Warns below zero; values carry forward over missing rate dates. Exact source dates appear below." />
      </div>
      <p className="callout info mt">A rolling average can remain above its trend after a sharp daily fall. These are smoothed signals. The monthly switch uses the original model and its own historical results.</p>
    </Section>
    <Section id="performance" eyebrow="Daily version backtest" title="Its own historical performance." intro={<>Recomputed from {b.start} through {b.end}: {b.sessions.toLocaleString()} sessions. SPY dividend-adjusted returns, cash interest and 0.10% cost per allocation change. Signals execute at the following session’s close.</>}>
      <div className="grid g4 kpis">
        <Metric title="Annual return" a={pct(b.strategy.cagr)} b={pct(b.buyhold.cagr)} />
        <Metric title="Worst drawdown" a={pct(b.strategy.max_dd)} b={pct(b.buyhold.max_dd)} />
        <Metric title="Sharpe ratio" a={num(b.strategy.sharpe)} b={num(b.buyhold.sharpe)} />
        <Metric title="Growth of $1" a={`$${num(b.strategy.final_multiple)}`} b={`$${num(b.buyhold.final_multiple)}`} />
      </div>
      <p className="sub">Main figure: rolling Bulwark · comparison: buy and hold SPY over the identical dates. Average equity allocation {pct(b.avg_equity, 0)}; {b.trades} allocation changes including entry.</p>
      <GrowthChart b={b} />
      <details className="card mt"><summary>Exact chart values</summary><div style={{ maxHeight: 320, overflow: 'auto' }}><table className="mat"><thead><tr><th>Date</th><th>Rolling Bulwark</th><th>Buy and hold</th></tr></thead><tbody>{b.dates.map((d, i) => <tr key={d}><td>{d}</td><td>{num(b.strategy_curve[i], 4)}</td><td>{num(b.buyhold_curve[i], 4)}</td></tr>)}</tbody></table></div></details>
      <p className="callout mt">This is a separate, hypothetical daily backtest using about ten years of available daily history, with roughly thirteen months reserved for rolling-window warm-up. It does not inherit the monthly model’s 1970–2026 results. Valuation and adjusted prices use revised historical data; this is not a real-time vintage reconstruction. SPY includes fund expenses; taxes and spreads are excluded. No parameters were selected to improve these results.</p>
    </Section>
    <Section id="method" eyebrow="Method & sources" title="What updates, and when.">
      <div className="card"><p>Trend: 21-session price average versus 210-session average. Momentum: 21-session dividend-adjusted price average versus its value 252 sessions ago, compared with compounded cash over the same 252-session span. Curve: prior-session daily Treasury rates. Each warning reduces equity by 25, 33⅓ or 40 points according to the original monthly valuation regime.</p>
      <p>Monthly valuation enters only after its month has ended. A signal from session t is executed at session t+1’s close and first earns the t+1 to t+2 return. Cash accrues over calendar days, including weekends. Computation uses only earlier observations, but historical source revisions remain a limitation.</p>
      <p>Updates are scheduled after each trading day. Incomplete current-day bars are excluded. The page checks for a new saved reading every 15 minutes; each input retains its own date.</p>
      <ul>{data.sources.map(s => <li key={s.name}><a href={s.url} target="_blank" rel="noreferrer">{s.name}</a> · data through {s.asof}</li>)}</ul>
      <p><a href="data/rolling.json" download>Download rolling model and performance data</a></p></div>
    </Section>
    <footer className="footer"><div className="wrap"><p>Bulwark · Rolling daily v1 · prices through {data.asof} · generated {data.generated}</p><p>Research simulation, not investment advice. Historical performance does not guarantee future results.</p></div></footer>
  </>
}

function Signal({ title, warning, value, detail }: { title: string; warning: boolean; value: string; detail: string }) {
  return <div className="card ind"><div className="ind-head"><h3>{title}</h3><Status ok={!warning} /></div><div className="value">{value}</div><p className="foot">{detail}</p></div>
}
function Metric({ title, a, b }: { title: string; a: string; b: string }) {
  return <div className="card kpi"><div className="label">{title}</div><div className="vals"><span className="main">{a}</span><span className="vs">vs <i>{b}</i></span></div></div>
}
function GrowthChart({ b }: { b: RollingData['backtest'] }) {
  const w = 1000, h = 340, left = 55, right = 20, top = 25, bottom = 35
  const max = Math.max(...b.strategy_curve, ...b.buyhold_curve) * 1.05
  const x = (i: number) => left + i / (b.dates.length - 1) * (w - left - right)
  const y = (v: number) => h - bottom - v / max * (h - top - bottom)
  const path = (a: number[]) => a.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ')
  return <div className="card mt"><p><span style={{ color: 'var(--s1)' }}>● Rolling Bulwark</span> · <span style={{ color: 'var(--ink-3)' }}>● Buy and hold SPY</span> · Growth of $1</p><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Growth of one dollar from ${b.start} to ${b.end}. Rolling Bulwark ends at ${num(b.strategy.final_multiple)}, buy and hold at ${num(b.buyhold.final_multiple)}.`} style={{ width: '100%', height: 'auto' }}>
    {[0, 1, 2, 3, 4].map(i => { const v = max * i / 4; return <g key={i}><line x1={left} x2={w - right} y1={y(v)} y2={y(v)} stroke="var(--ink-3)" opacity=".2" /><text x={left - 8} y={y(v) + 4} textAnchor="end" fill="var(--ink-2)" fontSize="12">${v.toFixed(1)}</text></g> })}
    <path d={path(b.buyhold_curve)} fill="none" stroke="var(--ink-3)" strokeWidth="2" /><path d={path(b.strategy_curve)} fill="none" stroke="var(--s1)" strokeWidth="2.5" />
    <text x={left} y={h - 8} fill="var(--ink-2)" fontSize="12">{b.start}</text><text x={w - right} y={h - 8} textAnchor="end" fill="var(--ink-2)" fontSize="12">{b.end}</text>
  </svg></div>
}
