import { useState } from 'react'
import type { Model } from '../types'
import { Gauge } from '../charts/Gauge'
import { monthLabel, pct, num, regimeLabel } from '../format'
import { Reveal, Status } from './ui'

const PERIOD_KEYS = ['full', 'since1990', 'since2010', 'lost_decades', 'holdout'] as const
const PERIOD_LABELS: Record<(typeof PERIOD_KEYS)[number], string> = { full: '1970 – today', since1990: '1990 –', since2010: '2010 –', lost_decades: '2000 – 2012', holdout: '1940 – 69 holdout' }

export function Hero({ model }: { model: Model }) {
  const s = model.snapshot
  const [pk, setPk] = useState<(typeof PERIOD_KEYS)[number]>('full')
  const P = model.headline[pk]
  const b = P.metrics.bulwark, h = P.metrics.buyhold
  const full = model.headline.full.metrics

  return (
    <header className="hero">
      <div className="wrap">
        <div className="hero-grid">
          <div>
            <span className="pill"><i className="dot" /> Live signal · {monthLabel(s.asof)} close</span>
            <h1>Stay invested.<br /><span className="grad">Step aside before it breaks.</span></h1>
            <p className="lead">
              Bulwark is a transparent, rules-based shield for U.S. equities. It reads trend, the yield curve, CAPE and the Buffett
              indicator — with <b>no fitted parameters</b> and <b>no peeking at the future</b>. Since 1970 it kept the compounding
              ({pct(full.bulwark.cagr)} vs {pct(full.buyhold.cagr)} a year) while cutting the worst drawdown from {pct(full.buyhold.max_dd, 0)} to {pct(full.bulwark.max_dd, 0)}.
            </p>
            <div className="hero-cta">
              <a className="btn primary" href="#signal">See today’s signal →</a>
              <a className="btn" href="#evidence">Is it overfit? Check the evidence</a>
            </div>
          </div>

          <Reveal>
            <div className="card signal-card" aria-label="Current allocation signal">
              <div className="signal-top"><span>Recommended equity exposure</span><span className="mono">next review: end of {monthLabel(s.next_month).split(' ')[0]}</span></div>
              <div className="gauge-wrap">
                <Gauge value={s.weight} label={`Equity exposure ${Math.round(s.weight * 100)} percent`} />
                <div className="gauge-center">
                  <div className="big">{Math.round(s.weight * 100)}<span style={{ fontSize: 26, color: 'var(--ink-3)' }}>%</span></div>
                  <div className="cap">in equities</div>
                </div>
              </div>
              <div className="signal-rows">
                <div className="sig-row"><span>Warning votes</span><span><b className="mono">{s.n_flags} of 3</b> &nbsp;<Status ok={s.n_flags === 0} okText="All clear" badText="Caution" /></span></div>
                <div className="sig-row"><span>Valuation regime</span><span className={`tag ${s.regime === 'rich' ? 'rich' : s.regime === 'cheap' ? 'cheap' : 'neutral'}`}>{regimeLabel(s.regime)}</span></div>
                <div className="sig-row"><span>S&amp;P 500 vs 10-month average</span><b className="mono">{pct(s.price_vs_sma, 1, true)}</b></div>
              </div>
            </div>
          </Reveal>
        </div>

        <Reveal>
          <div style={{ marginTop: 40 }} className="range-row">
            <div>
              <div style={{ fontWeight: 650, fontSize: 18 }}>The track record, in four numbers</div>
              <div className="sub" style={{ color: 'var(--ink-3)', fontSize: 13.5 }}>Monthly, total return incl. dividends, 0.10 % trading cost, {P.months} months. Hypothetical backtest.</div>
            </div>
            <div className="seg" role="group" aria-label="Period">
              {PERIOD_KEYS.map((k) => <button key={k} aria-pressed={pk === k} onClick={() => setPk(k)}>{PERIOD_LABELS[k]}</button>)}
            </div>
          </div>
          <div className="grid g4 kpis">
            <Kpi win={b.max_dd > h.max_dd} label="Worst drawdown" main={pct(b.max_dd, 1)} vs={pct(h.max_dd, 1)} note={`Buy & hold lost ${pct(Math.abs(h.max_dd), 0)} at the worst point.`} />
            <Kpi win={b.cagr >= h.cagr} label="Annual return (CAGR)" main={pct(b.cagr, 1)} vs={pct(h.cagr, 1)} note={b.cagr >= h.cagr ? 'Upside preserved over the full window.' : `Gives up ${pct(h.cagr - b.cagr, 1)} a year here — the price of insurance.`} />
            <Kpi win={(b.sharpe ?? 0) > (h.sharpe ?? 0)} label="Sharpe ratio" main={num(b.sharpe)} vs={num(h.sharpe)} note="Return per unit of volatility, over cash." />
            <Kpi win={b.down_capture < b.up_capture} label="Up / down capture" main={`${Math.round(b.up_capture * 100)} / ${Math.round(b.down_capture * 100)}`} vs="100 / 100" note="Share of up-month gains vs down-month losses taken." />
          </div>
          <p style={{ color: 'var(--ink-3)', fontSize: 13, marginTop: 10 }}>Large figure = Bulwark · “vs” figure = buy &amp; hold the S&amp;P 500 (total return). Blue highlight = Bulwark is better on that measure.</p>
        </Reveal>
      </div>
    </header>
  )
}

function Kpi({ label, main, vs, note, win }: { label: string; main: string; vs: string; note: string; win: boolean }) {
  return (
    <div className={`card kpi ${win ? 'win' : ''}`}>
      <div className="label">{label}</div>
      <div className="vals"><span className="main">{main}</span><span className="vs">vs <i>{vs}</i></span></div>
      <div className="note">{note}</div>
    </div>
  )
}
