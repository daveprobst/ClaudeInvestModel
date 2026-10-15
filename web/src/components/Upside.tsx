import { useMemo, useState } from 'react'
import type { Model } from '../types'
import { TimeChart } from '../charts/TimeChart'
import { pct } from '../format'
import { Reveal, Section } from './ui'

export function Upside({ model }: { model: Model }) {
  const m = model.headline.full.metrics
  const r = model.rolling10
  const [hover, setHover] = useState<number | null>(null)
  const dates = useMemo(() => r.series.map((s) => s.d), [r])
  const diff = useMemo(() => r.series.map((s) => s.b - s.h), [r])
  const [hy, setHy] = useState<number | null>(null)
  const cal = model.calendar
  const maxAbs = 0.25

  const color = (d: number) => {
    const t = Math.min(1, Math.abs(d) / maxAbs)
    const base = d >= 0 ? 'var(--div-pos)' : 'var(--div-neg)'
    return `color-mix(in srgb, ${base} ${Math.round(t * 85)}%, var(--div-mid))`
  }
  const cell = hy != null ? cal.find((c) => c.year === hy) : null

  return (
    <Section id="upside" eyebrow="What it costs"
      title={<>Protection isn’t free. <span className="grad">Here is the bill.</span></>}
      intro="Any shield that sells weakness will sometimes sit out a rally. The honest question is how much — and whether the trade is worth it across decades, not just in crashes.">
      <div className="grid g2">
        <Reveal><div className="card">
          <h3>Capture ratios, 1970 – today</h3>
          <div className="sub">Share of buy &amp; hold’s monthly gain / loss that Bulwark takes</div>
          <div className="stack" style={{ marginTop: 22, gap: 22 }}>
            <Capture label="Up months" v={m.bulwark.up_capture} color="var(--s1)" />
            <Capture label="Down months" v={m.bulwark.down_capture} color="var(--s1)" />
          </div>
          <p className="lede" style={{ marginTop: 22, fontSize: 15 }}>Bulwark takes about <b>{Math.round(m.bulwark.up_capture * 100)} %</b> of the good months but only <b>{Math.round(m.bulwark.down_capture * 100)} %</b> of the bad ones. Average equity exposure was {pct(m.bulwark.avg_equity, 0)}; a static mix with the <i>same</i> average exposure compounds only {pct(m.static.cagr, 1)} a year and still falls {pct(m.static.max_dd, 0)} — so the timing, not just the lower risk, does the work.</p>
        </div></Reveal>
        <Reveal><div className="card">
          <h3>Every 10-year window since 1970</h3>
          <div className="sub">Bulwark annual return minus buy &amp; hold, by start month</div>
          <div style={{ marginTop: 10 }}>
            <TimeChart dates={dates} lines={[{ key: 'd', label: 'Δ vs buy & hold', color: 'var(--s1)', values: diff, area: true, fillOpacity: 0.2, endLabel: false }]}
              height={210} scale="linear" format={(v) => pct(v, 0, true)} domain={[-0.06, 0.08]} ticks={[-0.05, 0, 0.05]} zeroLine hover={hover} setHover={setHover} rightPad={12}
              ariaLabel="Rolling ten-year annual return difference" />
          </div>
          <div className="grid g3" style={{ marginTop: 14, gap: 10 }}>
            <Tiny k="Ahead in" v={pct(r.share_bulwark_ahead, 0)} />
            <Tiny k="Within 1 pt" v={pct(r.share_within_1pt, 0)} />
            <Tiny k="Worst gap" v={pct(r.worst_diff, 1)} />
          </div>
          <p className="sub" style={{ marginTop: 12 }}>Worst 10 years: Bulwark {pct(r.worst_bulwark, 1, true)} a year vs buy &amp; hold {pct(r.worst_buyhold, 1, true)}. Median worst drawdown inside a 10-year window: {pct(r.median_dd_bulwark, 0)} vs {pct(r.median_dd_buyhold, 0)}.</p>
        </div></Reveal>
      </div>

      <Reveal><div className="card mt">
        <div className="chart-head">
          <div><h3>Calendar years vs buy &amp; hold</h3><div className="sub">Blue = Bulwark ahead · red = behind · scale ±25 pts</div></div>
          <div className="mono" style={{ fontSize: 13.5, color: 'var(--ink-2)', minHeight: 22 }} aria-live="polite">
            {cell ? <>{cell.year}: Bulwark <b style={{ color: 'var(--ink)' }}>{pct(cell.bulwark, 1, true)}</b> · buy &amp; hold <b style={{ color: 'var(--ink)' }}>{pct(cell.buyhold, 1, true)}</b> · equity {pct(cell.avg_equity, 0)}</> : 'Hover or tap a year'}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(58px, 1fr))', gap: 5 }}>
          {cal.map((c) => (
            <button key={c.year} onMouseEnter={() => setHy(c.year)} onFocus={() => setHy(c.year)} onClick={() => setHy(c.year)}
              aria-label={`${c.year}: Bulwark ${pct(c.bulwark, 1)}, buy and hold ${pct(c.buyhold, 1)}`}
              style={{ background: color(c.bulwark - c.buyhold), border: 0, borderRadius: 9, padding: '8px 2px', color: Math.abs(c.bulwark - c.buyhold) > 0.12 ? '#fff' : 'var(--ink)', cursor: 'pointer', font: 'inherit' }}>
              <div style={{ fontSize: 11, opacity: 0.8 }}>{c.year}</div>
              <div className="mono" style={{ fontSize: 13, fontWeight: 650 }}>{pct(c.bulwark, 0)}</div>
            </button>
          ))}
        </div>
        <p className="sub" style={{ marginTop: 14 }}>Cell number = Bulwark’s return that year. Its biggest give-ups are rebound and late-bull years (1975, 2009, 2019, 2020, 2023–24, up to −16 pts); its biggest gains are the bear years (2008 +28 pts, 1974 +22, 2002 +16, 2001 +13).</p>
      </div></Reveal>
    </Section>
  )
}

function Capture({ label, v, color }: { label: string; v: number; color: string }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}><span style={{ color: 'var(--ink-2)', fontWeight: 550 }}>{label}</span><b className="mono" style={{ fontSize: 28, letterSpacing: '-0.05em' }}>{Math.round(v * 100)}%</b></div>
      <div className="bar" style={{ height: 12 }}><i style={{ width: `${Math.min(100, v * 100)}%`, background: color }} /><u style={{ left: '100%', marginLeft: -2 }} /></div>
    </div>
  )
}
function Tiny({ k, v }: { k: string; v: string }) {
  return <div className="win-stat"><div className="k">{k}</div><div className="mono" style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.04em' }}>{v}</div></div>
}
