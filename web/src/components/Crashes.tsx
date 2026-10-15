import { useMemo, useState } from 'react'
import type { Model } from '../types'
import { useInView } from '../hooks'
import { monthLabel, pct } from '../format'
import { Legend, Reveal, Section } from './ui'

const NAMES: Record<string, string> = {
  '1940-04': 'Wartime sell-off', '1946-05': 'Post-war bear market', '1957-07': '1957 recession', '1961-12': 'Kennedy slide',
  '1966-01': '1966 credit crunch', '1968-12': 'Nifty-Fifty peak', '1973-01': 'Oil shock bear market', '1987-08': 'Black Monday',
  '2000-08': 'Dot-com bust', '2007-10': 'Global financial crisis', '2020-02': 'COVID crash', '2021-12': 'Inflation bear market',
}

export function Crashes({ model }: { model: Model }) {
  const [era, setEra] = useState<'modern' | 'all'>('modern')
  const eps = useMemo(() => model.episodes.filter((e) => (era === 'all' ? true : e.peak >= '1970-01')).slice().reverse(), [model.episodes, era])
  const [ref, seen] = useInView<HTMLDivElement>()
  const scale = 0.55 // bar track = 55 % drawdown
  const better = eps.filter((e) => e.bulwark_max_dd > e.buyhold_max_dd).length
  const avg = (f: (e: (typeof eps)[number]) => number) => eps.reduce((s, e) => s + f(e), 0) / eps.length
  const win = eps.filter((e) => e.bulwark_full_cycle > e.buyhold_full_cycle).length

  return (
    <Section id="crashes" eyebrow="Crash scorecard"
      title={<>Every major drawdown, <span className="grad">scored against buy &amp; hold.</span></>}
      intro="Episodes are identified from the S&P 500 itself (any decline of 15 % or more), then every strategy is judged over exactly the same window — no cherry-picking, including the ones where Bulwark did badly.">
      <Reveal>
        <div className="card" ref={ref}>
          <div className="chart-head">
            <div>
              <div style={{ fontWeight: 650, fontSize: 18 }}>Deepest loss inside each episode</div>
              <div className="sub">Peak → trough, measured on each strategy’s own value</div>
            </div>
            <div style={{ display: 'grid', gap: 10, justifyItems: 'end' }}>
              <div className="seg" role="group" aria-label="Era">
                <button aria-pressed={era === 'modern'} onClick={() => setEra('modern')}>Since 1970</button>
                <button aria-pressed={era === 'all'} onClick={() => setEra('all')}>Incl. 1940–69</button>
              </div>
              <Legend items={[{ label: 'Buy & hold', color: 'var(--s2)' }, { label: 'Bulwark', color: 'var(--s1)' }, { label: '10-month rule only', color: 'var(--s3)', dash: true }]} />
            </div>
          </div>

          <div className="grid g3" style={{ margin: '4px 0 12px' }}>
            <Mini k="Average worst loss" a={pct(avg((e) => e.bulwark_max_dd), 0)} b={pct(avg((e) => e.buyhold_max_dd), 0)} />
            <Mini k="Shallower loss in" a={`${better} of ${eps.length}`} b="episodes" plain />
            <Mini k="Ahead after full recovery" a={`${win} of ${eps.length}`} b="episodes" plain />
          </div>

          {eps.map((e) => {
            const rows = [
              { k: 'Buy & hold', v: e.buyhold_max_dd, c: 'var(--s2)' },
              { k: 'Bulwark', v: e.bulwark_max_dd, c: 'var(--s1)' },
              { k: '10-month rule only', v: e.faber_max_dd, c: 'var(--s3)', thin: true },
            ]
            return (
              <div className="crash" key={e.peak}>
                <div className="when">{NAMES[e.peak] ?? 'Drawdown'}<small>{monthLabel(e.peak)} → {monthLabel(e.trough)}</small></div>
                <div className="bars">
                  {rows.map((r) => (
                    <div className="hbar" key={r.k} title={`${r.k}: ${pct(r.v, 1)}`}>
                      <div className="track" style={r.thin ? { height: 6 } : undefined}><div className="fill" style={{ background: r.c, width: seen ? `${Math.min(100, (Math.abs(r.v) / scale) * 100)}%` : 0 }} /></div>
                      <b>{pct(r.v, 0)}</b>
                    </div>
                  ))}
                </div>
                <div className="side">
                  <b>{pct(e.bulwark_equity_at_trough, 0)}</b>equity at trough
                  <div style={{ marginTop: 6 }}>full cycle <span className="mono" style={{ color: 'var(--ink-2)' }}>{pct(e.bulwark_full_cycle, 0, true)}</span> vs <span className="mono" style={{ color: 'var(--ink-2)' }}>{pct(e.buyhold_full_cycle, 0, true)}</span></div>
                </div>
              </div>
            )
          })}
        </div>
      </Reveal>
      <div className="grid g2 mt">
        <div className="callout good"><b>Where it shines:</b> slow-motion bears — 1973–74, 2000–02, 2007–09 — where trend and the yield curve flip months before the lows. Bulwark’s deepest loss was under −20 % in each, versus −39 % to −49 % for buy &amp; hold.</div>
        <div className="callout"><b>Where it can’t:</b> crashes that start and end inside a month or two — 1987 and COVID-2020. A monthly rule can’t sidestep a 30-day cliff, and it re-enters after the rebound (2020: −3 % over the cycle vs +5 %). Nothing here predicts shocks; it limits how long a bear can hurt.</div>
      </div>
    </Section>
  )
}

function Mini({ k, a, b, plain }: { k: string; a: string; b: string; plain?: boolean }) {
  return (
    <div className="win-stat" style={{ padding: '14px 16px' }}>
      <div className="k">{k}</div>
      <div className="mono" style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.04em' }}>
        <span style={{ color: plain ? 'var(--ink)' : 'var(--s1)' }}>{a}</span>{' '}
        <span style={{ fontSize: 14, color: 'var(--ink-3)', fontWeight: 500 }}>{plain ? b : `vs ${b} buy & hold`}</span>
      </div>
    </div>
  )
}
