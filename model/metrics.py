"""Performance and risk statistics on monthly return series."""
from __future__ import annotations

import numpy as np
import pandas as pd


def equity_curve(r: pd.Series) -> pd.Series:
    return (1 + r.fillna(0)).cumprod()


def drawdown(curve: pd.Series) -> pd.Series:
    return curve / curve.cummax() - 1


def cagr(r: pd.Series) -> float:
    n = r.notna().sum()
    return float((1 + r.dropna()).prod() ** (12 / n) - 1)


def ann_vol(r: pd.Series) -> float:
    return float(r.std() * np.sqrt(12))


def sharpe(r: pd.Series, rf: pd.Series) -> float:
    ex = (r - rf).dropna()
    return float(ex.mean() / ex.std() * np.sqrt(12)) if ex.std() > 0 else float("nan")


def sortino(r: pd.Series, rf: pd.Series) -> float:
    ex = (r - rf).dropna()
    dd = np.sqrt((np.minimum(ex, 0) ** 2).mean())
    return float(ex.mean() / dd * np.sqrt(12)) if dd > 0 else float("nan")


def max_dd(r: pd.Series) -> float:
    return float(drawdown(equity_curve(r)).min())


def ulcer(r: pd.Series) -> float:
    d = drawdown(equity_curve(r))
    return float(100 * np.sqrt((d**2).mean()))


def capture(r: pd.Series, bench: pd.Series) -> tuple[float, float]:
    """Up/down capture: compounded strategy return / compounded benchmark return in up / down months."""
    j = pd.concat([r, bench], axis=1).dropna()
    j.columns = ["s", "b"]
    up, dn = j[j.b > 0], j[j.b < 0]

    def ann(x):  # geometric mean monthly
        return (1 + x).prod() ** (1 / len(x)) - 1

    return float(ann(up.s) / ann(up.b)), float(ann(dn.s) / ann(dn.b))


def summary(r: pd.Series, bench: pd.Series, rf: pd.Series) -> dict:
    uc, dc = capture(r, bench)
    return dict(
        cagr=cagr(r), vol=ann_vol(r), sharpe=sharpe(r, rf), sortino=sortino(r, rf), max_dd=max_dd(r),
        ulcer=ulcer(r), calmar=cagr(r) / abs(max_dd(r)) if max_dd(r) < 0 else float("nan"),
        up_capture=uc, down_capture=dc, worst_12m=float((equity_curve(r) / equity_curve(r).shift(12) - 1).min()),
        pct_positive_years=float((r.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1) > 0).mean()),
        final_multiple=float(equity_curve(r).iloc[-1]),
    )


def drawdown_episodes(r: pd.Series, threshold: float = 0.20) -> pd.DataFrame:
    """Peak-to-recovery episodes of the *series itself* deeper than ``threshold``."""
    c = equity_curve(r)
    dd = drawdown(c)
    rows, in_ep, peak_i, trough_i = [], False, None, None
    idx = c.index
    for i, t in enumerate(idx):
        if dd.iloc[i] == 0:
            if in_ep and dd.iloc[trough_i] <= -threshold:
                rows.append((idx[peak_i], idx[trough_i], t, float(dd.iloc[trough_i])))
            in_ep, peak_i = False, i
        else:
            if not in_ep:
                in_ep, trough_i = True, i
            if dd.iloc[i] < dd.iloc[trough_i]:
                trough_i = i
    if in_ep and dd.iloc[trough_i] <= -threshold:
        rows.append((idx[peak_i], idx[trough_i], None, float(dd.iloc[trough_i])))
    return pd.DataFrame(rows, columns=["peak", "trough", "recovery", "depth"])
