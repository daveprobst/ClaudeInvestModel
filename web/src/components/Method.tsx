import type { Model } from '../types'
import { monthLabel } from '../format'
import { Reveal, Section } from './ui'

const PARAMS: [string, string, string][] = [
  ['Moving average', '10 months', 'Faber (2007). The most-cited trend filter; also 200-day ≈ 10 months.'],
  ['Momentum', '12 months vs T-bills', 'Time-series momentum literature (Moskowitz–Ooi–Pedersen 2012; Antonacci).'],
  ['Yield curve', '10y − 3m < 0', 'Estrella–Mishkin (1996): inversion as a recession lead indicator. Zero is the definition, not a choice.'],
  ['“Rich” valuation', 'top 20 % of own past', 'A quintile. Percentile is computed only on data available at the time (expanding window).'],
  ['“Cheap” valuation', 'below the median', 'Below the historical median of the combined CAPE / Buffett percentile.'],
  ['Valuation min. history', '20 years', 'Don’t judge a level until at least two decades of context exist.'],
  ['Step per warning', '25 % / 33 % / 40 %', 'Three equal votes = 33 % each; softer when cheap, harder when rich (crashes from high valuations run deeper).'],
  ['Trading cost', '0.10 % of traded amount', 'Same as the earlier research; sensitivity to 0.5 % is shown above.'],
  ['Cash / defensive asset', '3-month T-bills', 'Simplest possible; 10-year Treasuries shown as a sensitivity.'],
  ['Leverage / shorting', 'none', 'Equity weight is always between 0 % and 100 %.'],
]
const LAGS: [string, string, string][] = [
  ['S&P 500 price & total return', 'Shiller monthly averages', 'Known at month-end. Trades are modelled at the month-end close (half-month blend, see below).'],
  ['CAPE', 'earnings lagged 3 months', 'Re-computed point-in-time; tracks Shiller’s published series within ~1 % on average.'],
  ['Buffett indicator', 'Fed Z.1 + GDP, 3-month lag', 'Latest published quarter, rolled forward with the S&P 500 move since then.'],
  ['Unemployment (Sahm)', '1-month lag', 'Jobs report arrives early the following month. A missing Oct-2025 reading is carried forward.'],
  ['Yield curve / credit', 'same month', 'Daily rates averaged over the month, known at month-end.'],
]

export function Method({ model }: { model: Model }) {
  return (
    <Section id="method" eyebrow="Method"
      title={<>Four steps. <span className="grad">Every number explained.</span></>}
      intro="The whole model fits on one screen. If a rule can’t be explained in a sentence and traced to public data, it isn’t in here.">
      <div className="grid g4">
        {[
          ['1', 'Read the tape', 'Is the S&P 500 below its 10-month average? Is its 12-month return below T-bills? Two votes.'],
          ['2', 'Read the cycle', 'Is the yield curve (10-year minus 3-month) inverted? One vote.'],
          ['3', 'Judge valuation', 'Rank CAPE and the Buffett indicator against their own past. Rich, fair or below-median sets the vote size.'],
          ['4', 'Size the position', 'Equity = 100 % − step × votes. The rest sits in T-bills. Re-checked each month-end.'],
        ].map(([n, t, d]) => (
          <Reveal key={n}><div className="card principle">
            <div className="ico mono" style={{ fontWeight: 700, fontSize: 18 }}>{n}</div><h3>{t}</h3><p>{d}</p>
          </div></Reveal>
        ))}
      </div>

      <div className="split mt2">
        <Reveal><div className="card">
          <h3>Parameters &amp; why they have those values</h3>
          <div className="sub" style={{ marginBottom: 12 }}>None were tuned on the backtest.</div>
          <div className="tbl-wrap"><table className="tbl params">
            <thead><tr><th>Rule</th><th>Value</th><th>Reason</th></tr></thead>
            <tbody>{PARAMS.map(([a, b, c]) => <tr key={a}><td>{a}</td><td>{b}</td><td>{c}</td></tr>)}</tbody>
          </table></div>
        </div></Reveal>
        <Reveal><div className="card">
          <h3>Timing: what is known, and when</h3>
          <div className="sub" style={{ marginBottom: 12 }}>Row <i>t</i> contains only what was public at the close of month <i>t</i>.</div>
          <div className="tbl-wrap"><table className="tbl params">
            <thead><tr><th>Input</th><th>Lag</th><th>Note</th></tr></thead>
            <tbody>{LAGS.map(([a, b, c]) => <tr key={a}><td>{a}</td><td style={{ whiteSpace: 'normal' }}>{b}</td><td>{c}</td></tr>)}</tbody>
          </table></div>
          <p className="sub" style={{ marginTop: 12 }}>Shiller’s prices are monthly <i>averages</i>, so the “month <i>t</i>” return is the move from mid-<i>t−1</i> to mid-<i>t</i>. A trade at the close of <i>t−1</i> sits exactly halfway, so the weight earning that return is ½ × old + ½ × new — no future information leaks into a past return. Acting a full month late (extra-conservative) is in the sensitivity table.</p>
        </div></Reveal>
      </div>

      <Reveal><div className="card mt">
        <h3>Limitations — read before relying on any of this</h3>
        <ul className="clean" style={{ marginTop: 14 }}>
          <li><b>It’s a backtest.</b> One U.S. history, roughly eight bear markets. Strong statistics on a small number of independent events.</li>
          <li><b>Designer hindsight is unavoidable.</b> I know 2000 and 2008 happened. Mitigations: conventional parameters, a pre-1970 holdout, foreign markets, and full disclosure of the one design change that was driven by in-sample diagnostics (dropping credit &amp; Sahm).</li>
          <li><b>Valuation is a weak timer.</b> The market has been “rich” since the mid-1990s. Here it only scales how hard trend warnings cut; on its own it never sells.</li>
          <li><b>Fast crashes beat a monthly rule</b> (1987, 2020), and whipsaws cost a few points in choppy years.</li>
          <li><b>Averaged prices smooth volatility.</b> Month-end data would show slightly larger drawdowns for <i>both</i> strategy and benchmark.</li>
          <li><b>Data revisions.</b> Fed Z.1, GDP and Shiller’s earnings are today’s revised vintages; real-time values differed slightly.</li>
          <li><b>Costs &amp; taxes.</b> 0.10 % per trade is assumed; taxes, bid-ask spreads on large size, and fund fees are not modelled.</li>
          <li><b>Not advice.</b> Research and education only; see the disclaimer below.</li>
        </ul>
      </div></Reveal>

      <Reveal><div className="card mt src">
        <h3>Data sources</h3>
        <div className="tbl-wrap" style={{ marginTop: 10 }}><table className="tbl params">
          <thead><tr><th>Source</th><th>Used for</th><th>Latest</th></tr></thead>
          <tbody>{model.sources.map((s) => <tr key={s.name}><td><a href={s.url} target="_blank" rel="noreferrer">{s.name}</a></td><td>{s.used_for}</td><td style={{ textAlign: 'right' }}>{/^\d{4}-\d{2}$/.test(s.last) ? monthLabel(s.last) : s.last}</td></tr>)}</tbody>
        </table></div>
      </div></Reveal>
    </Section>
  )
}
