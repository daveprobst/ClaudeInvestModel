"""Daily rolling research variant, separate from the original monthly simulation.

SPY adjusted close supplies dividend-adjusted returns. Signals observed at t's
close execute at t+1's close and first earn returns at t+2. Monthly valuation
observations enter on the first day of the following month. These are revised
historical inputs, not an archived real-time vintage dataset.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .config import PARAMS
from .data import RAW, ROOT, load_raw
from .signals import compute_signals


def load_equity(today=None):
    r = json.loads((RAW / "SPY.json").read_text())["chart"]["result"][0]
    dates = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()
    df = pd.DataFrame({"price": r["indicators"]["quote"][0]["close"],
                       "total_return": r["indicators"]["adjclose"][0]["adjclose"]}, index=dates).dropna()
    today = pd.Timestamp.now(tz="America/New_York").date() if today is None else pd.Timestamp(today).date()
    # Exclude today's possibly unfinished session, including a live Yahoo bar.
    return df.loc[df.index.date < today].sort_index()


def load_rates():
    def read(name):
        d = pd.read_csv(RAW / f"{name}.csv", index_col=0, parse_dates=True)
        return pd.to_numeric(d.iloc[:, 0], errors="coerce").dropna()
    return pd.concat({"long": read("DGS10"), "short": read("DTB3")}, axis=1, sort=True)


def daily_signals(equity, rates, monthly):
    d = equity.copy()
    # Align each input on its own date before filling; never backfill from the future.
    rates = rates.copy()
    for col in ["long", "short"]:
        rates[col + "_date"] = rates.index.to_series().where(rates[col].notna())
    known = rates.reindex(rates.index.union(d.index)).sort_index().ffill().reindex(d.index).shift(1)
    # End-of-month valuation becomes available on the following calendar day.
    m = monthly[["regime", "step"]].copy()
    m["valuation_asof"] = m.index.astype(str)
    m.index = m.index.to_timestamp(how="end").normalize() + pd.Timedelta(days=1)
    m = m.reindex(m.index.union(d.index)).sort_index().ffill().reindex(d.index)
    d = d.join(m)
    d["short"] = known["short"]
    d["curve"] = known["long"] - known["short"]
    d["long_date"], d["short_date"] = known["long_date"], known["short_date"]
    d["fast"] = d.price.rolling(21, min_periods=21).mean()
    d["slow"] = d.price.rolling(210, min_periods=210).mean()
    smooth_tr = d.total_return.rolling(21, min_periods=21).mean()
    d["momentum"] = smooth_tr / smooth_tr.shift(252) - 1
    # Calendar-day cash accrual accommodates weekends and exchange holidays.
    days = d.index.to_series().diff().dt.days
    d["cash_return"] = (1 + d["short"] / 100) ** (days / 365.25) - 1
    cash = (1 + d.cash_return.fillna(0)).cumprod()
    d["cash12"] = cash / cash.shift(252) - 1
    d["trend_warning"] = d.fast < d.slow
    d["momentum_warning"] = d.momentum < d.cash12
    d["curve_warning"] = d.curve < 0
    d["warnings"] = d[["trend_warning", "momentum_warning", "curve_warning"]].sum(axis=1)
    d["weight"] = (1 - d.step * d.warnings).clip(0, 1)
    valid = d[["slow", "momentum", "cash12", "curve", "step"]].notna().all(axis=1)
    d.loc[~valid, "weight"] = np.nan
    return d


def simulate(d):
    out = d.copy()
    out["buyhold"] = out.total_return.pct_change(fill_method=None)
    out["effective_weight"] = out.weight.shift(2)
    out["turnover"] = (out.weight.shift(2) - out.weight.shift(3)).abs()
    # Charge the initial move from cash into the strategy as well.
    first = out.effective_weight.first_valid_index()
    if first is not None:
        out.loc[first, "turnover"] = abs(out.loc[first, "effective_weight"])
    out["strategy"] = (out.effective_weight * out.buyhold +
                       (1 - out.effective_weight) * out.cash_return - out.turnover * PARAMS.cost_per_trade)
    return out.dropna(subset=["strategy", "buyhold", "cash_return"])


def stats(r, cash):
    c = pd.Series(np.r_[1.0, (1 + r).cumprod().to_numpy()])
    years = ((r.index[-1] - r.index[0]).days + 1) / 365.25
    excess = r - cash
    return dict(cagr=float(c.iloc[-1] ** (1 / years) - 1),
                max_dd=float((c / c.cummax() - 1).min()),
                sharpe=float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() else None,
                final_multiple=float(c.iloc[-1]))


def build():
    raw = load_raw()
    d = daily_signals(load_equity(), load_rates(), compute_signals(raw))
    bt = simulate(d)
    if bt.empty or pd.isna(d.weight.iloc[-1]):
        raise ValueError("Insufficient rolling history or current inputs")
    s = d.iloc[-1]
    curve = lambda r: np.r_[1.0, (1 + r).cumprod().to_numpy()].round(6).tolist()
    result = dict(
        version="rolling-daily-v1", generated=str(pd.Timestamp.now(tz="UTC")),
        asof=str(d.index[-1].date()), instrument="SPY (S&P 500 ETF)",
        snapshot=dict(price=float(s.price), fast=float(s.fast), slow=float(s.slow),
                      momentum=float(s.momentum), cash12=float(s.cash12), curve=float(s.curve),
                      weight=float(s.weight), warnings=int(s.warnings), regime=s.regime,
                      valuation_asof=s.valuation_asof,
                      long_rate_asof=str(s.long_date.date()), short_rate_asof=str(s.short_date.date()),
                      flags={k: bool(s[k]) for k in ["trend_warning", "momentum_warning", "curve_warning"]}),
        backtest=dict(start=str(bt.index[0].date()), end=str(bt.index[-1].date()), sessions=len(bt),
                      strategy=stats(bt.strategy, bt.cash_return), buyhold=stats(bt.buyhold, bt.cash_return),
                      avg_equity=float(bt.effective_weight.mean()), trades=int((bt.turnover > 1e-9).sum()),
                      # Include starting capital so drawdown and the chart include the first loss.
                      dates=["Start"] + [str(t.date()) for t in bt.index],
                      strategy_curve=curve(bt.strategy), buyhold_curve=curve(bt.buyhold)),
        sources=[dict(name="SPY daily close and dividend-adjusted close (Yahoo Finance)",
                      url="https://finance.yahoo.com/quote/SPY/history/", asof=str(d.index[-1].date())),
                 dict(name="10-year Treasury and 3-month T-bill (FRED)",
                      url="https://fred.stlouisfed.org/series/DGS10", asof=str(s.long_date.date())),
                 dict(name="3-month Treasury bill rate (FRED DTB3)",
                      url="https://fred.stlouisfed.org/series/DTB3", asof=str(s.short_date.date())),
                 dict(name="Completed-month valuation regime (original Bulwark)",
                      url="https://shillerdata.com", asof=s.valuation_asof)],
    )
    dest = ROOT / "web/public/data/rolling.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")))
    bt.to_csv(ROOT / "outputs/rolling_daily_paths.csv", float_format="%.8f")
    print("Rolling daily:", result["asof"], result["snapshot"])
    print("Backtest:", {k: v for k, v in result["backtest"].items() if "curve" not in k and k != "dates"})
    return result


if __name__ == "__main__":
    build()
