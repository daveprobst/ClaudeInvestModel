import { useMemo } from 'react'
import { scaleLinear } from 'd3-scale'
import { line as d3line, curveMonotoneX } from 'd3-shape'
import { useSize } from '../hooks'

export function Sparkline({ values, height = 54, color = 'var(--s1)', refValue, label }: { values: (number | null)[]; height?: number; color?: string; refValue?: number; label: string }) {
  const [ref, w] = useSize<HTMLDivElement>()
  const g = useMemo(() => {
    const v = values.filter((x): x is number => x != null)
    if (!v.length || w < 10) return null
    const x = scaleLinear().domain([0, values.length - 1]).range([2, w - 6])
    const y = scaleLinear().domain([Math.min(...v), Math.max(...v)]).range([height - 6, 6])
    const path = d3line<number | null>().defined((d) => d != null).x((_, i) => x(i)).y((d) => y(d as number)).curve(curveMonotoneX)(values) ?? ''
    let j = values.length - 1
    while (values[j] == null && j > 0) j--
    return { path, x: x(j), y: y(values[j] as number), refY: refValue != null ? y(refValue) : null }
  }, [values, w, height, refValue])
  return (
    <div ref={ref}>
      <svg width={w} height={height} role="img" aria-label={label} style={{ display: 'block' }}>
        {g?.refY != null && <line x1={0} x2={w} y1={g.refY} y2={g.refY} stroke="var(--ink-3)" strokeDasharray="3 4" opacity={0.6} />}
        {g && <path d={g.path} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" />}
        {g && <circle cx={g.x} cy={g.y} r={4} fill={color} stroke="var(--surface)" strokeWidth={2} />}
      </svg>
    </div>
  )
}
