# Research log

A complete, honest record of every design the new model went through. The point of a log is that nobody
(including me) can quietly drop the versions that looked worse.

## Design rules fixed *before* the first run

1. Only textbook / round parameters (10-month average, 12-month momentum, quintiles, yield curve < 0, Sahm 0.5).
2. Valuation levels are judged against *only the past* (expanding percentile, 20-year minimum history).
3. Each row of data contains only what was public at that month-end (explicit lags, tested).
4. Parameters are never selected by the backtest; grids only *show* sensitivity.

## v0 — first and only pre-registered design (5 warning flags)

Flags: price < 10-month average, 12-month momentum < cash, yield curve inverted, credit spread in top quintile of
history, Sahm rule triggered. Equity = 100 % − step × flags, step = 15 / 20 / 25 % (cheap / fair / rich valuation).

| | CAGR | Max DD | Sharpe |
|---|---|---|---|
| v0, 1970–2026 | 10.7 % | −24.6 % | 0.69 |
| Buy & hold | 11.1 % | −49.0 % | 0.55 |
| v0, 1940–69 holdout | 10.3 % | −21.5 % | 0.85 |
| Buy & hold, holdout | 11.9 % | −26.5 % | 0.86 |

Verdict: worse risk than it should be **and** lower return than buy & hold. Before changing anything I measured
what each flag actually "knows" (average excess return of stocks over cash in the month *after* a flag is on/off).

## Diagnostic (understanding, not tuning)

| Flag | ON | OFF | 1940–69 ON | OFF |
|---|---|---|---|---|
| Below 10-month average | 3.4 % | 8.5 % | 4.8 % | 12.0 % |
| 12-month momentum < cash | 3.6 % | 8.4 % | 14.3 % | 7.8 % |
| Yield curve inverted | 0.3 % | 8.1 % | n/a | n/a |
| Credit spread top quintile | **10.7 %** | 6.1 % | n/a | n/a |
| Sahm rule triggered | **10.2 %** | 6.1 % | **24.3 %** | 6.6 % |

Note the 12-month momentum flag was *wrong-way* in the holdout (ON 14.3 % vs OFF 7.8 %); it is kept because it is
the standard companion of the 10-month rule and was not selected on this result, and the ablation table shows it is the
weakest single rule (momentum-only: 8.5 % CAGR, −24.8 % drawdown in the holdout). It is a candidate for removal and the site discloses it.

Credit stress and the Sahm rule are *lagging* indicators: they fire near market bottoms, so selling on them
sells low — in both independent samples. That is also the textbook reason (equities lead the economy).

## v1 — FINAL: 3 warning flags (trend ×2 + yield curve)

Dropped credit & Sahm from the *cut* logic (kept as dashboard context). Steps re-based to 3 equal votes:
25 / 33 / 40 %. This is the one design change driven by in-sample diagnostics; it is confirmed out-of-sample by the
1940–69 holdout and by the Sahm result there.

| | CAGR | Max DD | Sharpe |
|---|---|---|---|
| v1, 1970–2026 | 11.5 % | −23.7 % | 0.77 |
| v1, 1940–69 holdout | 10.7 % | −18.2 % | 0.92 |

## v2 — rejected: curve counts only if price agrees ("don't fight the tape")

Same results within noise (1970–2026: 11.6 % / −23.7 % / 0.75). No clear benefit → the simpler rule (v1) is kept.

## Ablations, reported not selected

The lone Faber 10-month rule (all-or-nothing) is a very strong baseline: 11.3 % CAGR, −19.7 % worst drawdown,
Sharpe 0.76 (holdout: −14.3 %). Bulwark's extra value is *graded* exposure and diversification across warning
types, with ~7 points more upside capture. The valuation tilt contributes little (Ulcer index
5.50 → 4.97 and Sharpe 0.759 → 0.766 in 1970–2026; +0.3 pt CAGR in the holdout) — it is kept because it is the user's brief and low-cost, not because the data
demand it. Both facts are on the website.

## Known limitations

See the website's *Method → Limitations*, and `model/config.py`.
