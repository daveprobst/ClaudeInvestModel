"""Backtest engine.

Timing (the part that is easiest to get wrong, so it is spelled out):

* Signals at row ``t`` use only information public at the close of month ``t`` (see signals.py).
* The portfolio is rebalanced to ``w_target[t]`` *at that close*.
* Equity returns come from Shiller's total-return index, which is built from monthly AVERAGES of daily
  prices. The return of "month t" is therefore the move from the middle of t-1 to the middle of t. A trade
  at the close of t-1 sits exactly halfway through that window, so the weight that earns the month-t
  return is   w_eff[t] = 0.5 * w[t-2] + 0.5 * w[t-1]   -- the old weight for the first half, the new one for
  the second. No month-t information ever influences a return that happened before it was known.
* Cash earns the 3-month T-bill rate. Every trade costs ``cost_per_trade`` of the amount traded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PARAMS, Params
from .data import Raw
from .signals import compute_signals


def run_weights(
    r_eq: pd.Series,
    r_cash: pd.Series,
    w: pd.Series,
    cost: float,
    lag_mode: str = "half",
    r_alt: pd.Series | None = None,
) -> pd.DataFrame:
    """Simulate a target-weight path. ``r_alt`` (optional) replaces cash as the defensive asset."""
    w = w.reindex(r_eq.index)
    w1, w2 = w.shift(1), w.shift(2)
    if lag_mode == "half":
        w_eff = 0.5 * w1 + 0.5 * w2
        turnover = (w1 - w2).abs()
    elif lag_mode == "full":      # extra-conservative: act one full month later
        w_eff = w2
        turnover = (w2 - w.shift(3)).abs()
    else:
        raise ValueError(lag_mode)
    defensive = r_cash if r_alt is None else r_alt
    ret = w_eff * r_eq + (1 - w_eff) * defensive - turnover * cost
    out = pd.DataFrame({"ret": ret, "w_eff": w_eff, "w_signal": w1, "turnover": turnover})
    return out.dropna(subset=["ret"])


def backtest(raw: Raw, p: Params = PARAMS, sig: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    """Full backtest frame: strategy, buy&hold, cash, plus the signals that drove each month."""
    sig = compute_signals(raw, p) if sig is None else sig
    idx = sig.index
    r_eq = sig["tr_index"].pct_change()
    r_cash = (raw.tb3.reindex(idx) / 1200.0)
    sim = run_weights(r_eq, r_cash, sig["w_target"], p.cost_per_trade, **kw)
    out = sig.join(sim, how="inner")
    out["r_bh"] = r_eq.reindex(out.index)
    out["r_cash"] = r_cash.reindex(out.index)
    return out


def window(df: pd.DataFrame, start: str, end: str | None = None) -> pd.DataFrame:
    return df.loc[start:end] if end else df.loc[start:]
