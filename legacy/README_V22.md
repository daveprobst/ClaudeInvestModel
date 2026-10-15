# V22 valuation + systemic-stress model

This folder is a frozen, standalone reproduction bundle for V22. It contains
the runner, the complete source dependency chain, frozen input data, source
manifests, and regenerated proof outputs. V22 is research code, not personal
investment advice.

## Run

From this folder:

```bash
python3 -m pip install -r requirements.txt
./run_v22.sh
```

Alternatively:

```bash
python3 run_v22.py
```

The runner resolves every path relative to this folder, executes the frozen
model only through the V22 definition, and recreates `proof/`. The authoritative
source is `model/v21.py` for the V22 wrapper and `model/portfolio5.py` for the
state machine. Exact raw-input hashes are in `model/data_manifest.json` and
`model/macro_manifest.json`.

## Portfolio and return series

- Monthly test period: January 1971 through August 2026.
- Reporting currency: CHF.
- Initial sleeves: 30% US, 30% Europe and 40% Switzerland.
- Sleeves evolve independently; there is no periodic rebalance back to
  30/30/40.
- US: S&P 500 total return using Shiller dividends.
- Europe: German index through 1986 chained to the euro-area index, with an
  assumed 3% annual dividend yield.
- Switzerland: Swiss price index with an assumed 2.5% annual dividend yield.
- US and European equity returns are fully CHF-hedged using short-rate
  differentials. Signals use local-currency monthly-average prices.

Every purchase and sale costs 0.1% of the amount traded.

## Valuation and trend signal

For each indicator, calculate its percentile over the latest 300 months,
including the current observation, with at least 120 valid observations:

```text
percentile = count(window values <= current value) / valid window values
```

US valuation is the lower of:

- the rolling Shiller CAPE percentile; and
- the rolling Buffett-proxy percentile.

The Buffett proxy is S&P 500 price divided by interpolated nominal US GDP,
scaled so March 2000 equals 145. Using the lower percentile means both US
valuation indicators must be high.

European and Swiss valuation is the rolling percentile of local price divided
by interpolated local nominal GDP.

For sleeve `k`, the ordinary sell condition is:

```text
valuation_percentile[k,t] >= 0.90
AND price[k,t] < arithmetic_10_month_average[k,t]
```

V22 uses the current indexed monthly-average observation and transacts at that
same monthly index. This is an important same-month timing limitation of the
historical simulation.

## Systemic-stress signal

Construct a local-price index without dividends or currency conversion:

```text
mix[t] = 0.30 * US_price[t] / US_price[0]
       + 0.30 * EU_price[t] / EU_price[0]
       + 0.40 * CH_price[t] / CH_price[0]
```

Its drawdown is `mix / running_max(mix) - 1`. A raw systemic observation is:

```text
mix_drawdown[t] <= -10%
AND (NFCI[t] >= 1 OR monthly_max_VIX[t] >= 40)
```

The raw observation is shifted one month before execution and applies to all
three sleeves. V22 has no breadth requirement and no external event latch.
NFCI is the final weekly value in each month; VIX is the maximum daily close.

## Sell state

A sleeve can begin selling only while `IN` and outside its cooldown. Its own
valuation/trend condition or the portfolio-wide systemic condition can start
the exit. Once started, the exit completes even if the signal disappears.

The three monthly equity targets are produced by:

```text
target(t) = w0 * (1 - log(1 + 30*t) / log(1 + 30*3)), t < 3
target(3) = 0
```

From 100% equity, the targets are 23.8729%, 8.8672%, and 0%.

Sale proceeds remain within the original sleeve:

- US reserve: approximate US 10-year Treasuries, CHF hedged.
- European reserve: approximate German 10-year bonds, CHF hedged.
- Swiss reserve: CHF cash.

Bond growth uses duration 7 and convexity 60:

```text
1 + prior_yield/1200 - 7*yield_change + 30*yield_change^2
```

## Crash deployment

Each sleeve tracks its running local-price peak and valuation at that peak.
After reaching 0% equity, its crash trigger and pacing are:

| Peak valuation | Trigger | Pacing divisor | Immediate buy |
|---|---:|---:|---:|
| At least 90th percentile | -30% | 48 | 10% of reserve |
| 75th to below 90th | -25% | 42 | 15% of reserve |
| Below 75th or missing | -20% | 36 | 15% of reserve |

After the immediate purchase, fixed monthly amount `M` is remaining reserve
divided by the pacing divisor. Beginning in the following month, `M` is added
to an internal bank. The bank is invested whenever price is above its 10-month
average. Otherwise it remains in the reserve asset.

The following once-only checkpoints purchase a percentage of reserve remaining
at that time:

| Drawdown from stored peak | Purchase |
|---|---:|
| -30% | 15% |
| -40% | 20% |
| -50% | 25% |
| -60% | 35% |
| -70% | 50% |

A checkpoint at or above the initial trigger is marked completed. At month 36
after the crash trigger, the accumulated bank and all remaining reserve are
invested. The 42/48 divisors therefore slow early buying but never extend the
hard completion deadline beyond 36 months.

## Valuation all-clear re-entry

If no crash trigger has fired, an `OUT` sleeve begins ordinary re-entry when:

```text
valuation_percentile[k,t] < 0.70
AND price[k,t] > 10_month_average[k,t]
AND the systemic force is false
```

The reserve is nominally divided by 12. No purchase occurs in the signal
month. V22 buys one amount in each following month, then in the eleventh
following month buys one normal amount and all residual reserve. Thus the exact
implementation places twelve nominal tranches over eleven purchase months,
with a double final month. Preserve this quirk for numerical replication.

After either re-entry route finishes, the sleeve returns to `IN` and cannot
start another sale for 12 months.

## State priority

1. `IN`: an eligible sell signal can start a sale.
2. `SELLING`: finish the three-month exit unconditionally.
3. `OUT`: a crash trigger has priority over all-clear.
4. `DEPLOY`: ignore new sell signals.
5. `REENTRY`: ignore new sell signals.
6. After reinvestment, apply the 12-month cooldown.

This suppression of new exits during deployment and re-entry is part of V22,
not an implementation accident.

## Portfolio value and expected reproduction

For each sleeve:

```text
sleeve_value = equity_units * CHF_total_return_index + reserve_value
portfolio = 0.30*US_sleeve + 0.30*EU_sleeve + 0.40*CH_sleeve
```

With the included frozen inputs, the expected result is:

| Metric | V22 | Lump sum |
|---|---:|---:|
| Ending value per initial CHF | 81.400384 | 74.938068 |
| CAGR | 8.236587% | 8.075631% |
| Maximum drawdown | -21.936424% | -50.349610% |
| Ulcer index | 8.820267 | 14.881480 |

Current V22 equity allocation is 100%.

## Proof outputs

Running the bundle recreates:

- `proof/metrics.json`
- `proof/monthly_paths.csv`
- `proof/switch_events.csv`
- `proof/crash_episodes.csv`
- `proof/01_v22_performance.png`
- `proof/02_v22_execution.png`
- `proof/03_v22_robustness.png`
- `proof/engine_log.txt`

The metrics file is the quickest machine-readable reproduction check.
