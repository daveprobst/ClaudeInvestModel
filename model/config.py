"""Bulwark -- every model parameter lives here, frozen, with the reason it has that value.

DESIGN RULES (anti-overfitting contract)
----------------------------------------
1. Every number below is a *textbook / round convention* that existed before this model:
   10-month average (Faber 2007), 12-month momentum (Moskowitz-Ooi-Pedersen 2012, Antonacci),
   quintiles (top 20% = "rich"), Sahm rule 0.5pp (Sahm 2019), yield-curve inversion < 0.
2. NOTHING was fitted, swept or optimised on the backtest. The sensitivity grids in
   ``model/analysis.py`` only *show* that nearby values behave alike; they never select values.
3. Information is strictly point-in-time: each row ``t`` only contains data that was public at the
   close of month ``t`` (publication lags are applied in ``signals.py``). The automated test
   ``tests/test_no_lookahead.py`` re-computes every signal from data truncated at ``t`` and checks
   it equals the full-history value.
4. Valuation levels are judged against *only the past* (expanding percentile). No full-sample
   statistics, no level calibrated to a known peak (the legacy model scaled the Buffett proxy so that
   March 2000 = 145% -- that is hindsight and is gone).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Params:
    # ---- Trend pillar -----------------------------------------------------------------
    sma_months: int = 10          # Faber (2007) "A Quantitative Approach to Tactical Asset Allocation"
    mom_months: int = 12          # 12-month time-series momentum vs. cash (Antonacci / MOP 2012)

    # ---- Macro / credit pillar --------------------------------------------------------
    curve_inversion: float = 0.0  # 10y yield minus 3m bill below 0 => inverted (Estrella-Mishkin 1996)
    sahm_threshold: float = 0.5   # Sahm rule: 3m avg unemployment 0.5pp above its 12m low
    credit_pct_stress: float = 0.80   # Baa-10y spread in the top quintile of its own past => stress

    # ---- Valuation regime (CAPE + Buffett indicator) ----------------------------------
    pct_min_history: int = 240    # 20 years of past data before a percentile is trusted
    val_rich: float = 0.80        # top quintile of own history => "rich"
    val_cheap: float = 0.50       # below the historical median => "cheap"
    cape_earnings_lag: int = 3    # earnings are reported ~3 months late -> CAPE uses E up to t-3
    cape_years: int = 10          # the "10" in CAPE
    z1_lag_months: int = 3        # Fed Z.1 / GDP for quarter ending q is public by q+3 months
    unrate_lag_months: int = 1    # jobs report for month t is released early in t+1

    # ---- Which flags cut equity ---------------------------------------------------------
    # See docs/RESEARCH_LOG.md: credit-stress and Sahm are *lagging* (they fire near bottoms, after the
    # damage; forward equity returns were ABOVE average when they were on, in both the 1970+ sample and the
    # 1940-69 holdout), so they are shown on the dashboard but do not cut equity.
    cut_flags: tuple = ("below_sma", "neg_mom", "curve_inv")
    curve_needs_trend: bool = False  # tested (v2): gating the curve by trend was not clearly better -> simpler rule kept

    # ---- Allocation: each warning flag removes this much equity -----------------------
    step_cheap: float = 1 / 4     # cheap market: bear markets from low valuations are shallower
    step_fair: float = 1 / 3      # 3 equal votes: all three warnings => fully defensive
    step_rich: float = 2 / 5      # rich market: crashes from high valuations run deeper
    max_equity: float = 1.0       # never leveraged
    min_equity: float = 0.0       # never short

    # ---- Frictions ----------------------------------------------------------------------
    cost_per_trade: float = 0.001  # 0.10% of the amount traded (same as the legacy model)

    # ---- Sample -------------------------------------------------------------------------
    start: str = "1970-01"        # main sample: >=25y of Buffett-indicator history exists by then
    holdout_start: str = "1940-01"  # pre-1970 holdout: valuation falls back to CAPE only
    holdout_end: str = "1969-12"


PARAMS = Params()

FLAG_LABELS = {
    "below_sma": "Price below 10-month average",
    "neg_mom": "12-month momentum below cash",
    "curve_inv": "Yield curve inverted (10y < 3m)",
    "credit_stress": "Credit spreads in top quintile of history",
    "sahm": "Sahm recession rule triggered",
}
