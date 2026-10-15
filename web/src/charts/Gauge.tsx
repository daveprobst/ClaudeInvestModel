import { useEffect, useState } from 'react'

/** 240° arc gauge, 0–100 %. Animates from 0 on mount. */
export function Gauge({ value, label }: { value: number; label: string }) {
  const [v, setV] = useState(0)
  useEffect(() => { const t = setTimeout(() => setV(value), 150); return () => clearTimeout(t) }, [value])
  const R = 112, C = 140, start = 150, sweep = 240
  const pt = (deg: number, r = R) => [C + r * Math.cos((deg * Math.PI) / 180), C + r * Math.sin((deg * Math.PI) / 180)]
  const arc = (a0: number, a1: number, r = R) => {
    const [x0, y0] = pt(a0, r), [x1, y1] = pt(a1, r)
    return `M ${x0} ${y0} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}`
  }
  const end = start + sweep * Math.max(0.0001, v)
  const ticks = [0, 0.25, 0.5, 0.75, 1]
  const [kx, ky] = pt(end)
  return (
    <svg viewBox="0 0 280 236" width="100%" style={{ maxWidth: 320 }} role="img" aria-label={label}>
      <defs>
        <linearGradient id="gaugeGrad" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="var(--s3)" /><stop offset="1" stopColor="var(--s1)" />
        </linearGradient>
        <filter id="gaugeGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6" /></filter>
      </defs>
      <path d={arc(start, start + sweep)} fill="none" stroke="var(--surface-3)" strokeWidth={16} strokeLinecap="round" />
      <path d={arc(start, end)} fill="none" stroke="url(#gaugeGrad)" strokeWidth={16} strokeLinecap="round" style={{ transition: 'all 1s cubic-bezier(.2,.8,.2,1)' }} />
      <path d={arc(start, end)} fill="none" stroke="var(--s1)" strokeWidth={16} strokeLinecap="round" opacity={0.35} filter="url(#gaugeGlow)" />
      {ticks.map((t) => {
        const a = start + sweep * t
        const [x0, y0] = pt(a, R + 16), [x1, y1] = pt(a, R + 22), [tx, ty] = pt(a, R + 36)
        return (
          <g key={t}>
            <line x1={x0} y1={y0} x2={x1} y2={y1} stroke="var(--ink-3)" strokeWidth={1.5} />
            <text x={tx} y={ty} dy="0.35em" textAnchor="middle" fontSize={11} fill="var(--ink-3)" fontFamily="var(--mono)">{t * 100}</text>
          </g>
        )
      })}
      <circle cx={kx} cy={ky} r={9} fill="var(--surface)" stroke="var(--ink)" strokeWidth={3} style={{ transition: 'all 1s cubic-bezier(.2,.8,.2,1)' }} />
    </svg>
  )
}
