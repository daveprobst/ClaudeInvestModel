# Bulwark — a common-sense drawdown shield

A transparent, rules-based model that tries to **avoid the deep drawdowns of U.S. equities without giving up the
upside**, using only conventional, widely known indicators — 10-month moving average, 12-month momentum, the yield
curve, CAPE and the Buffett indicator — with **no fitted parameters** and **no look-ahead**.

* 🌐 Website: React dashboard with the live signal, interactive backtest, crash scorecard and the full robustness evidence (`web/`)
* 🧮 Model: ~1,000 lines of Python (incl. tests), one frozen config, leak-audit tests (`model/`)
* 🗃️ The earlier V1→V22 research is archived in [`legacy/`](legacy) with an [audit](docs/LEGACY_AUDIT.md) of why it was rebuilt

## The rules

Equity weight = 100 % − *step* × (number of active warnings), floored at 0, remainder in 3-month T-bills,
re-evaluated at each month-end.

| Warning | Rule |
|---|---|
| Trend | S&P 500 below its 10-month average |
| Momentum | 12-month total return below T-bills |
| Yield curve | 10-year minus 3-month yield < 0 |

The *step* depends on valuation (average of the expanding-window percentiles of CAPE and a Buffett indicator):
**25 %** if below the historical median, **33 %** otherwise, **40 %** if in the top quintile ("rich").
Credit spreads and the Sahm rule are computed and shown, but deliberately do **not** cut equity — they are lagging
indicators (see [`docs/RESEARCH_LOG.md`](docs/RESEARCH_LOG.md)).

## Results (monthly, total return, 0.10 % cost per trade)

| 1970 – Sep 2026 | CAGR | Worst drawdown | Sharpe | Up / down capture |
|---|---|---|---|---|
| **Bulwark** | 11.5 % | −23.7 % | 0.77 | 80 % / 59 % |
| Buy & hold S&P 500 | 11.1 % | −49.0 % | 0.55 | 100 % / 100 % |
| Static mix, same average equity | 9.8 % | −40.3 % | 0.55 | 81 % / 75 % |
| 10-month rule alone (Faber) | 11.3 % | −19.7 % | 0.76 | 73 % / 48 % |

Holdout 1940–1969 (never tuned on): drawdown −18 % vs −27 %, Sharpe 0.92 vs 0.86, **but 1.2 pts/yr lower return**.
Since 2010 it lags (11.3 % vs 14.2 %): protection costs upside in a one-way bull market.
A 3,000-draw block bootstrap says the Sharpe/drawdown improvement is very unlikely to be luck (98 % / ~100 %), while the
CAGR difference is statistically indistinguishable from zero.

Current signal (Sep 2026 close): **100 % equities, 0 of 3 warnings, valuation rich** (CAPE ≈ 41, 99th percentile).

## Why you can trust (or at least audit) it

* All parameters are round, pre-existing conventions — see [`model/config.py`](model/config.py).
* Every input is lagged to its real publication date; percentiles use only the past.
* [`model/tests/test_no_lookahead.py`](model/tests/test_no_lookahead.py) recomputes the signals and portfolio return
  from data truncated at 27 dates and demands exact equality. A mutation test (injecting a full-sample percentile) was
  verified to make it fail.
* Ablations, sensitivity grids, a pre-1970 holdout, eight international markets and a block bootstrap are
  produced by [`model/analysis.py`](model/analysis.py) and shown on the site.
* **Limitations** (one US history, designer hindsight, averaged prices, no taxes, …) are listed on the site and in the
  research log. This is research, not investment advice.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m model.run            # backtest + analysis -> web/public/data, outputs/
.venv/bin/python -m model.run --fetch    # re-download all public data first
.venv/bin/python -m pytest model/tests   # leak audit

cd web && npm ci && npm run dev          # website on http://localhost:5173
```

## Layout

```
model/          fetch.py · data.py · signals.py · engine.py · metrics.py · analysis.py · run.py · tests/
data/raw/       committed public data (Shiller, FRED) so results reproduce offline
web/            Vite + React + TypeScript site (hand-built SVG charts)
docs/           LEGACY_AUDIT.md · RESEARCH_LOG.md
legacy/         the original V1–V22 scripts and figures, untouched
render.yaml     Render blueprint (static site, free)
.github/        CI + monthly data refresh
```

## Deploy

`render.yaml` defines a free Render **static site** built from `web/` (`npm ci && npm run build`, publish `dist`).
Because the model output is committed as JSON, Render needs no Python. The monthly GitHub Action refreshes the data and
pushes, and Render redeploys automatically.
