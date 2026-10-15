"""Point-in-time signals.

Row ``t`` = what an investor knows at the *close of month t*. Prices are monthly averages (Shiller), which
are fully known at month-end. Everything published with a delay is shifted explicitly below:

    earnings (CAPE denominator) .... lag 3 months     (config.cape_earnings_lag)
    Fed Z.1 equity value & GDP ..... lag 3 months     (config.z1_lag_months)
    unemployment rate .............. lag 1 month      (config.unrate_lag_months)
    CPI ............................ lag 1 month      (only used to put CAPE earnings in today's dollars)
"""
from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

from .config import PARAMS, Params
from .data import Raw


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def expanding_pct(x: pd.Series, min_history: int) -> pd.Series:
    """Percentile of x_t within all observations up to and including t (never looks forward).

    pct_t = #{s <= t : x_s <= x_t} / #{s <= t}.  Needs ``min_history`` valid observations.
    """
    v = x.to_numpy(dtype=float)
    out = np.full(len(v), np.nan)
    seen: list[float] = []                       # kept sorted
    for i, xi in enumerate(v):
        if np.isnan(xi):
            continue
        bisect.insort(seen, xi)
        if len(seen) >= min_history:
            out[i] = bisect.bisect_right(seen, xi) / len(seen)
    return pd.Series(out, index=x.index)


def cape_point_in_time(sh: pd.DataFrame, p: Params) -> pd.Series:
    """CAPE_t = P_t / mean over 10y of real earnings, with earnings known only up to t-3 and every
    earnings figure re-based with the CPI known at t-1. Closely tracks Shiller's published CAPE."""
    cpi_known = sh["CPI"].shift(1)                              # CPI for month t is published in t+1
    real_e = (sh["E"] / sh["CPI"])                              # earnings in "CPI units"
    e10 = real_e.shift(p.cape_earnings_lag).rolling(p.cape_years * 12, min_periods=p.cape_years * 12).mean()
    return sh["P"] / (cpi_known * e10)


def buffett_point_in_time(sh: pd.DataFrame, raw: Raw, p: Params) -> pd.Series:
    """Market value of U.S. corporate equity / GDP, nowcast to month t.

    Anchor: last *published* quarter (quarter-end <= t - z1_lag_months). Roll forward with the S&P 500 price
    move since that quarter-end; the GDP denominator is the anchor quarter's SAAR GDP."""
    ratio_q = (raw.z1_equity / 1000.0) / raw.gdp                # both known by q + lag
    ratio_q = ratio_q.dropna()
    idx = sh.index
    out = pd.Series(np.nan, index=idx)
    q_ends = ratio_q.index
    for t in idx:
        # most recent quarter-end that is public at the close of t
        avail = q_ends[q_ends <= (t - p.z1_lag_months)]
        if len(avail) == 0:
            continue
        q = avail[-1]
        if q in sh.index:
            out[t] = ratio_q[q] * sh.at[t, "P"] / sh.at[q, "P"]
    return out


def sahm_gap(unrate: pd.Series, lag: int, index: pd.PeriodIndex) -> pd.Series:
    """3-month average unemployment minus its minimum over the prior 12 months (>= 0.5 => recession signal)."""
    # BLS skipped the Oct-2025 household survey (shutdown); carry the last value forward (causal, <=2 months)
    u = unrate.reindex(index).ffill(limit=2).shift(lag)
    u3 = u.rolling(3, min_periods=3).mean()
    low12 = u3.shift(1).rolling(12, min_periods=12).min()
    return u3 - low12


# --------------------------------------------------------------------------------------
# main entry
# --------------------------------------------------------------------------------------
def compute_signals(raw: Raw, p: Params = PARAMS) -> pd.DataFrame:
    sh = raw.shiller
    idx = sh.index
    df = pd.DataFrame(index=idx)
    df["price"] = sh["P"]
    df["tr_index"] = sh["tr_index"]

    # ---- trend ----
    df["sma"] = df["price"].rolling(p.sma_months, min_periods=p.sma_months).mean()
    df["below_sma"] = df["price"] < df["sma"]
    cash_m = (raw.tb3.reindex(idx) / 1200.0)
    cash_idx = (1 + cash_m.fillna(0)).cumprod()
    df["mom12"] = df["tr_index"] / df["tr_index"].shift(p.mom_months) - 1
    df["cash12"] = cash_idx / cash_idx.shift(p.mom_months) - 1
    mom_ok = df["mom12"].notna() & raw.tb3.reindex(idx).shift(p.mom_months - 1).notna()
    df["neg_mom"] = (df["mom12"] < df["cash12"]) & mom_ok

    # ---- macro / credit ----
    gs10 = raw.gs10.reindex(idx)
    tb3 = raw.tb3.reindex(idx)
    df["curve"] = gs10 - tb3
    df["curve_inv"] = (df["curve"] < p.curve_inversion) & df["curve"].notna()
    df["credit_spread"] = raw.baa.reindex(idx) - gs10
    df["credit_pct"] = expanding_pct(df["credit_spread"], p.pct_min_history)
    df["credit_stress"] = (df["credit_pct"] >= p.credit_pct_stress) & df["credit_pct"].notna()
    df["sahm_gap"] = sahm_gap(raw.unrate, p.unrate_lag_months, idx)
    df["sahm"] = (df["sahm_gap"] >= p.sahm_threshold - 1e-12) & df["sahm_gap"].notna()

    # ---- valuation ----
    df["cape"] = cape_point_in_time(sh, p)
    df["buffett"] = buffett_point_in_time(sh, raw, p)
    df["cape_pct"] = expanding_pct(df["cape"], p.pct_min_history)
    df["buffett_pct"] = expanding_pct(df["buffett"], p.pct_min_history)
    df["val_score"] = df[["cape_pct", "buffett_pct"]].mean(axis=1, skipna=True)   # NaN if neither exists
    regime = pd.Series("fair", index=idx)
    regime[df["val_score"] >= p.val_rich] = "rich"
    regime[df["val_score"] < p.val_cheap] = "cheap"
    df["regime"] = regime
    df["step"] = regime.map({"cheap": p.step_cheap, "fair": p.step_fair, "rich": p.step_rich})

    # ---- allocation ----
    cut = df[list(p.cut_flags)].copy()
    if p.curve_needs_trend and "curve_inv" in cut:
        trend_on = df["below_sma"] | df["neg_mom"]
        cut["curve_inv"] = cut["curve_inv"] & trend_on
    df["curve_active"] = cut["curve_inv"] if "curve_inv" in cut else False
    df["n_flags"] = cut.sum(axis=1)
    df["w_target"] = (p.max_equity - df["step"] * df["n_flags"]).clip(p.min_equity, p.max_equity)
    return df


FLAGS = ["below_sma", "neg_mom", "curve_inv", "credit_stress", "sahm"]
