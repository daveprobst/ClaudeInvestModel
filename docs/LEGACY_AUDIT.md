# Audit of the earlier research (V1 → V22)

The original work lives, untouched, in [`legacy/`](../legacy). This note records what was found when it was
reviewed, and why the model was rebuilt rather than patched. Everything below was verified against the files.

## 1. It could not be reproduced

* `README_V22.md` describes a bundle (`run_v22.py`, `model/v21.py`, `requirements.txt`, `proof/`, frozen data and
  manifests). **None of those files exist in the workspace.**
* The scripts read inputs that are missing: `sp.csv`, `gdp.csv`, `fx.csv`.
* 30 of the ~40 scripts chain to each other with `exec(open('other.py').read())` (e.g. `v10.py` executes a
  *string-split* of `v9.py`), so no module can be run or tested on its own.

## 2. Classic signs of an overfitting loop

* 27 numbered figures include a trigger sweep, threshold heat-maps and window-percentile studies
  (`1_trigger_sweep.png`, `7_threshold_heatmaps.png`, `22_window_percentiles.png`, `20_modelD_robustness.png`).
* `27_v6_comparison.png` shows successive versions lagging the lump-sum benchmark by 25–60 % before the
  next version "fixed" it. The final V22 edge over lump sum is **+0.16 %/yr CAGR** (8.24 % vs 8.08 %).
* V22 is specified by roughly forty hand-set numbers: a 300-month percentile window, 0.90/0.75/0.70 valuation
  gates, a `log(1+30t)` sell curve, pacing divisors 36/42/48, five drawdown checkpoints buying
  15/20/25/35/50 % of the reserve, a 12-month cooldown, "12 tranches over eleven months with a double final month"
  that the README says to *preserve for numerical replication*. A rule set that has to be preserved quirk-for-quirk
  to reproduce a result is a fit, not a principle.

## 3. Hindsight and look-ahead

| Where | What | Problem |
|---|---|---|
| `model3.py` L14–23 | Buffett proxy = S&P ÷ GDP, **scaled so March 2000 = 145 %** | Calibrated to a known bubble peak |
| `model3.py` L5–9 | CAPE after Sep 2023 extended by hand and "calibrated to CAPE 41.4 in Jul 2026" | Invented input; the real Jul-2026 value is 40.0 |
| `model3.py` L16 | Pre-1960 GDP typed in as a literal dict | Not fetched from a source, not verifiable |
| `README_V22.md` | Signals "transact at that same monthly index" | Same-month execution on monthly-*average* prices (acknowledged by the author) |
| `README_V22.md` | Europe/Switzerland dividends = assumed 3 % / 2.5 % constants | Not data |
| `model.py`, `model2.py` | Piece-wise constant CHF and USD short-rate tables typed from memory | Not data |
| `eudata.py`, `bonddata.py`, `chbond.py` | Index and yield series pasted as strings | Provenance only in comments |

## 4. What was kept

The *ideas* that survive scrutiny: valuation percentiles from CAPE and a Buffett-style ratio, 10-month trend,
reserve asset held in cash. They are now built on downloaded public data, with every publication lag explicit, and
evaluated against a pre-1970 holdout, foreign markets, ablations and a block bootstrap. See
[`RESEARCH_LOG.md`](RESEARCH_LOG.md).
