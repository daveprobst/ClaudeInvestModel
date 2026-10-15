import { useMemo, useRef, useState, type ReactNode } from 'react'
import { scaleLinear, scaleLog } from 'd3-scale'
import { line as d3line, area as d3area, curveStepAfter, curveMonotoneX } from 'd3-shape'
import { useSize } from '../hooks'
import { monthLabel } from '../format'

export type Line = {
  key: string; label: string; color: string; values: (number | null)[]
  dash?: string; width?: number; area?: boolean; step?: boolean; fillOpacity?: number; endLabel?: boolean
}
export type Band = { from: number; to: number; color: string }

type Props = {
  dates: string[]; lines: Line[]; height: number; scale?: 'log' | 'linear'
  format: (v: number) => string; domain?: [number, number]; ticks?: number[]
  hover: number | null; setHover: (i: number | null) => void
  bands?: Band[]; ariaLabel: string; zeroLine?: boolean; showXAxis?: boolean
  tooltipExtra?: (i: number) => ReactNode; rightPad?: number
}

const M = { top: 10, bottom: 26, left: 46 }

export function TimeChart(p: Props) {
  const [wrapRef, width] = useSize<HTMLDivElement>()
  const svgRef = useRef<SVGSVGElement>(null)
  const [active, setActive] = useState(false)
  const rightPad = p.rightPad ?? (width < 520 ? 62 : 78)
  const innerW = Math.max(10, width - M.left - rightPad)
  const bottom = p.showXAxis === false ? 6 : M.bottom
  const innerH = p.height - M.top - bottom
  const n = p.dates.length

  const { x, y, yTicks, paths } = useMemo(() => {
    const all = p.lines.flatMap((l) => l.values.filter((v): v is number => v != null))
    let lo = p.domain ? p.domain[0] : Math.min(...all)
    let hi = p.domain ? p.domain[1] : Math.max(...all)
    if (p.scale === 'log') { lo = Math.max(lo, 1e-6) }
    const x = scaleLinear().domain([0, n - 1]).range([0, innerW])
    const base = p.scale === 'log' ? scaleLog() : scaleLinear()
    const y = base.domain([lo, hi]).range([innerH, 0]).nice() as unknown as ((v: number) => number) & { ticks: (n?: number) => number[] }
    const t = p.ticks ?? (p.scale === 'log' ? y.ticks(5).filter((v) => Number.isFinite(v)) : y.ticks(4))
    const paths = p.lines.map((l) => {
      const ln = d3line<number | null>().defined((v) => v != null).x((_, i) => x(i)).y((v) => y(v as number)).curve(l.step ? curveStepAfter : curveMonotoneX)
      const ar = l.area
        ? d3area<number | null>().defined((v) => v != null).x((_, i) => x(i)).y0(y(p.scale === 'log' ? lo : Math.max(lo, Math.min(0, hi)))).y1((v) => y(v as number)).curve(l.step ? curveStepAfter : curveMonotoneX)
        : null
      return { line: ln(l.values) ?? '', area: ar ? ar(l.values) ?? '' : null }
    })
    return { x, y, yTicks: t, paths }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.lines, p.scale, p.domain, p.ticks, innerW, innerH, n])

  const xTicks = useMemo(() => {
    const span = Number(p.dates[n - 1].slice(0, 4)) - Number(p.dates[0].slice(0, 4))
    const step = span > 70 ? 10 : span > 35 ? 5 : span > 18 ? 2 : 1
    const out: { i: number; label: string }[] = []
    const seen = new Set<string>()
    p.dates.forEach((d, i) => { const yy = d.slice(0, 4); if (Number(yy) % step === 0 && !seen.has(yy)) { seen.add(yy); out.push({ i, label: yy }) } })
    return out
  }, [p.dates, n])

  const onMove = (e: React.PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect()
    const px = e.clientX - r.left - M.left
    p.setHover(Math.max(0, Math.min(n - 1, Math.round(x.invert(px)))))
  }

  // direct end labels, nudged apart
  const ends = useMemo(() => {
    const raw = p.lines.map((l) => {
      let j = l.values.length - 1
      while (j > 0 && l.values[j] == null) j--
      return { l, y: y(l.values[j] as number) as number }
    }).filter((e) => e.l.endLabel !== false)
    raw.sort((a, b) => a.y - b.y)
    for (let i = 1; i < raw.length; i++) if (raw[i].y - raw[i - 1].y < 15) raw[i].y = raw[i - 1].y + 15
    return raw
  }, [p.lines, y])

  const hov = p.hover
  const tipLeft = hov != null ? M.left + x(hov) : 0
  const flip = hov != null && x(hov) > innerW * 0.6

  return (
    <div ref={wrapRef} className="chart-rel">
      <svg ref={svgRef} className="chart-svg" width={width} height={p.height} role="img" aria-label={p.ariaLabel}
        onPointerMove={(e) => { setActive(true); onMove(e) }} onPointerLeave={() => { setActive(false); p.setHover(null) }}>
        <g transform={`translate(${M.left},${M.top})`}>
          {p.bands?.map((b, i) => <rect key={i} x={x(b.from)} width={Math.max(1, x(b.to) - x(b.from))} y={0} height={innerH} fill={b.color} />)}
          <g className="axis">
            {yTicks.map((t) => (
              <g key={t} transform={`translate(0,${y(t)})`}>
                <line x1={0} x2={innerW} />
                <text x={-10} dy="0.32em" textAnchor="end">{p.format(t)}</text>
              </g>
            ))}
            {p.showXAxis !== false && xTicks.map((t) => (
              <text key={t.i} x={x(t.i)} y={innerH + 18} textAnchor="middle">{t.label}</text>
            ))}
          </g>
          {p.zeroLine && <line x1={0} x2={innerW} y1={y(0)} y2={y(0)} stroke="var(--ink-3)" strokeWidth={1} opacity={0.6} />}
          {p.lines.map((l, i) => (
            <g key={l.key}>
              {paths[i].area && <path d={paths[i].area!} fill={l.color} opacity={l.fillOpacity ?? 0.16} />}
              <path d={paths[i].line} fill="none" stroke={l.color} strokeWidth={l.width ?? 2} strokeDasharray={l.dash} strokeLinejoin="round" strokeLinecap="round" />
            </g>
          ))}
          {ends.map((e) => (
            <text key={e.l.key} x={innerW + 8} y={e.y} dy="0.32em" fontSize={12} fontWeight={600} fill="var(--ink-2)">{e.l.label}</text>
          ))}
          {hov != null && (
            <g pointerEvents="none">
              <line x1={x(hov)} x2={x(hov)} y1={0} y2={innerH} stroke="var(--ink-3)" strokeDasharray="3 4" />
              {p.lines.map((l) => {
                const v = l.values[hov]
                return v == null ? null : <circle key={l.key} cx={x(hov)} cy={y(v)} r={4.5} fill={l.color} stroke="var(--surface)" strokeWidth={2} />
              })}
            </g>
          )}
        </g>
      </svg>
      {hov != null && active && (
        <div className="tooltip" style={{ top: 6, left: flip ? undefined : tipLeft + 16, right: flip ? width - tipLeft + 16 : undefined }} aria-hidden>
          <div className="t-date">{monthLabel(p.dates[hov])}</div>
          {p.lines.map((l) => (
            <div className="t-row" key={l.key}>
              <span><i className="dot" style={{ background: l.color }} />{l.label}</span>
              <b>{l.values[hov] == null ? '–' : p.format(l.values[hov] as number)}</b>
            </div>
          ))}
          {p.tooltipExtra?.(hov)}
        </div>
      )}
    </div>
  )
}
