import { useMemo, useState } from 'react'
import type { Model, Series } from '../types'
import { TimeChart, type Band, type Line } from '../charts/TimeChart'
import { drawdownSeries, windowStats } from '../stats'
import { monthLabel, mult, num, pct } from '../format'
import { Reveal, Section } from './ui'

const STARTS = [
  { y: 1940, label: '1940' }, { y: 1970, label: '1970' }, { y: 1990, label: '1990' }, { y: 2000, label: '2000 (dot-com)' }, { y: 2007, label: '2007 (GFC)' }, { y: 2010, label: '2010' },
]
type Key = 'bulwark' | 'buyhold' | 'faber' | 'cash'
const META: Record<Key, { label: string; color: string; dash?: string; width: number }> = {
  bulwark: { label: 'Bulwark', color: 'var(--s1)', width: 2.6 },
  buyhold: { label: 'Buy & hold', color: 'var(--s2)', width: 2.2 },
  faber: { label: '10-month rule only', color: 'var(--s3)', dash: '6 4', width: 1.9 },
  cash: { label: 'T-bills', color: 'var(--cash)', dash: '2 4', width: 1.8 },
}

export function Performance({ model, series }: { model: Model; series: Series }) {
  const [startY, setStartY] = useState(1970)
  const [log, setLog] = useState(true)
  const [on, setOn] = useState<Record<Key, boolean>>({ bulwark: true, buyhold: true, faber: false, cash: false })
  const [hover, setHover] = useState<number | null>(null)
  const [table, setTable] = useState(false)

  const lo = Math.max(0, series.d.findIndex((d) => d >= `${startY}-01`))
  const hi = series.d.length - 1
  const dates = useMemo(() => series.d.slice(lo), [series.d, lo])
  const keys = (Object.keys(META) as Key[]).filter((k) => on[k])

  const rebased = useMemo(() => {
    const out = {} as Record<Key, number[]>
    ;(Object.keys(META) as Key[]).forEach((k) => { const a = series[k]; out[k] = a.slice(lo).map((v) => v / a[lo]) })
    return out
  }, [series, lo])

  const growth: Line[] = keys.map((k) => ({ key: k, ...META[k], values: rebased[k] }))
  const dd: Line[] = keys.filter((k) => k !== 'cash').map((k) => ({
    key: k, ...META[k], values: drawdownSeries(series[k], lo, hi), area: k === 'buyhold' || k === 'bulwark', fillOpacity: k === 'buyhold' ? 0.10 : 0.18, endLabel: k !== 'faber',
  }))
  const expo: Line[] = [{ key: 'w', label: 'Equity', color: 'var(--s1)', values: series.w.slice(lo), area: true, step: true, fillOpacity: 0.28, width: 2 }]
  const bands: Band[] = useMemo(() => {
    const out: Band[] = []
    let i = 0
    const reg = series.regime.slice(lo)
    while (i < reg.length) {
      let j = i
      while (j + 1 < reg.length && reg[j + 1] === reg[i]) j++
      if (reg[i] === 2) out.push({ from: i, to: j, color: 'color-mix(in srgb, var(--warn) 10%, transparent)' })
      if (reg[i] === 0) out.push({ from: i, to: j, color: 'color-mix(in srgb, var(--s3) 12%, transparent)' })
      i = j + 1
    }
    return out
  }, [series.regime, lo])

  const stats = useMemo(() => {
    const r = {} as Record<Key, ReturnType<typeof windowStats>>
    ;(Object.keys(META) as Key[]).forEach((k) => { r[k] = windowStats(series[k], series.cash, lo, hi) })
    return r
  }, [series, lo, hi])

  const logTicks = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000].filter((t) => {
    const all = keys.flatMap((k) => rebased[k]); return t >= Math.min(...all) / 1.6 && t <= Math.max(...all) * 1.6
  })
  const linMax = Math.max(...keys.flatMap((k) => rebased[k]))
  const fmtMult = (v: number) => (v >= 10 ? `${Math.round(v)}×` : `${v.toFixed(1)}×`)

  const rows = useMemo(() => {
    const out: { y: string; b: number; h: number; f: number; w: number | null }[] = []
    series.d.forEach((d, i) => {
      if (i >= lo && (d.endsWith('-12') || i === hi) && i > lo) {
        const p = series.d.findIndex((x) => x === `${Number(d.slice(0, 4)) - 1}-12`)
        const pi = p < lo ? lo : p
        out.push({ y: d.slice(0, 4), b: series.bulwark[i] / series.bulwark[pi] - 1, h: series.buyhold[i] / series.buyhold[pi] - 1, f: series.faber[i] / series.faber[pi] - 1, w: series.w[i] })
      }
    })
    return out
  }, [series, lo, hi])

  return (
    <Section id="performance" eyebrow="Performance"
      title={<>Same destination. <span className="grad">A far smoother road.</span></>}
      intro="Drag across any chart — all three stay in sync. Pick a starting point to see how the story changes; the statistics below recompute for that window.">
      <Reveal>
        <div className="card chart-card">
          <div className="chart-head">
            <div className="seg" role="group" aria-label="Start year">
              {STARTS.map((s) => <button key={s.y} aria-pressed={startY === s.y} onClick={() => setStartY(s.y)}>{s.label}</button>)}
            </div>
            <div className="seg" role="group" aria-label="Scale">
              <button aria-pressed={log} onClick={() => setLog(true)}>Log</button>
              <button aria-pressed={!log} onClick={() => setLog(false)}>Linear</button>
            </div>
          </div>
          <div className="chart-head" style={{ marginBottom: 6 }}>
            <div className="legend" role="group" aria-label="Series">
              {(Object.keys(META) as Key[]).map((k) => (
                <button key={k} aria-pressed={on[k]} onClick={() => setOn((o) => ({ ...o, [k]: !o[k] }))}>
                  <i className={`swatch ${META[k].dash ? 'dash' : ''}`} style={{ background: META[k].color, color: META[k].color }} />{META[k].label}
                </button>
              ))}
            </div>
            <button className="toggle-link" onClick={() => setTable((t) => !t)}>{table ? 'Show charts' : 'View as table'}</button>
          </div>

          {!table ? (
            <div className="stackcharts">
              <div className="sub" style={{ margin: '8px 0 0' }}>Growth of $1 (total return, nominal)</div>
              <TimeChart dates={dates} lines={growth} height={330} scale={log ? 'log' : 'linear'} format={fmtMult}
                domain={log ? undefined : [0, linMax]} ticks={log ? logTicks : undefined} hover={hover} setHover={setHover}
                showXAxis={false} ariaLabel="Growth of one dollar for each strategy" />
              <div className="sub" style={{ margin: '10px 0 0' }}>Drawdown from previous peak</div>
              <TimeChart dates={dates} lines={dd} height={170} scale="linear" format={(v) => pct(v, 0)} domain={[Math.min(-0.5, ...dd.flatMap((l) => l.values as number[]))-0.02, 0]}
                ticks={[-0.5, -0.25, 0]} hover={hover} setHover={setHover} zeroLine showXAxis={false} ariaLabel="Drawdown from previous peak" />
              <div className="sub" style={{ margin: '10px 0 0' }}>Bulwark’s equity exposure <span style={{ color: 'var(--warn)' }}>■</span> rich valuation &nbsp;<span style={{ color: 'var(--s3)' }}>■</span> below-median valuation</div>
              <TimeChart dates={dates} lines={expo} height={140} scale="linear" format={(v) => pct(v, 0)} domain={[0, 1]} ticks={[0, 0.5, 1]}
                hover={hover} setHover={setHover} bands={bands} ariaLabel="Bulwark equity exposure over time"
                tooltipExtra={(i) => { const nf = series.nf[lo + i]; return <div className="t-row"><span>Warnings active</span><b>{nf} of 3</b></div> }} />
            </div>
          ) : (
            <div className="tbl-wrap" style={{ maxHeight: 520, overflowY: 'auto' }}>
              <table className="tbl">
                <caption className="sr-only">Calendar-year total returns</caption>
                <thead><tr><th>Year</th><th>Bulwark</th><th>Buy &amp; hold</th><th>10-month only</th><th>Avg equity</th></tr></thead>
                <tbody>{rows.map((r) => (
                  <tr key={r.y}><td>{r.y}</td><td className={r.b >= 0 ? '' : 'neg'}>{pct(r.b, 1)}</td><td className={r.h >= 0 ? '' : 'neg'}>{pct(r.h, 1)}</td><td>{pct(r.f, 1)}</td><td>{r.w == null ? '–' : pct(r.w, 0)}</td></tr>
                ))}</tbody>
              </table>
            </div>
          )}

          <div className="win-stats">
            <Stat title={`Annual return · ${monthLabel(dates[0])} →`} rows={keys.filter((k) => k !== 'cash').map((k) => [k, pct(stats[k].cagr, 1)])} />
            <Stat title="Worst drawdown" rows={keys.filter((k) => k !== 'cash').map((k) => [k, pct(stats[k].maxDd, 1)])} />
            <Stat title="Sharpe ratio" rows={keys.filter((k) => k !== 'cash').map((k) => [k, num(stats[k].sharpe, 2)])} />
            <Stat title="$1 becomes" rows={keys.map((k) => [k, mult(stats[k].final, stats[k].final >= 100 ? 0 : 1)])} />
          </div>
        </div>
      </Reveal>
      <p className="sub" style={{ marginTop: 14, color: 'var(--ink-3)', fontSize: 13 }}>
        Source: Shiller S&amp;P 500 total-return index (monthly averages), 3-month T-bills; {model.turnover_per_year.toFixed(2)}× annual turnover, about {model.trades_per_year.toFixed(1)} rebalances a year, 0.10 % cost per trade included. Past performance is hypothetical and not a guarantee.
      </p>
    </Section>
  )
}

function Stat({ title, rows }: { title: string; rows: [Key, string][] }) {
  return (
    <div className="win-stat">
      <div className="k">{title}</div>
      {rows.map(([k, v]) => (
        <div className="row" key={k}><span><i className="dot" style={{ width: 8, height: 8, borderRadius: 4, background: META[k].color, display: 'inline-block' }} />{META[k].label}</span><b>{v}</b></div>
      ))}
    </div>
  )
}
