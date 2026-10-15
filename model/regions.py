"""Region packs: run the *same* Bulwark rules on another market (premium feature, Switzerland demo).

Everything that cannot be sourced natively for the region is substituted by the U.S. series and **labelled as
such** in the output (``inputs`` list) so the website can show it. Rules, parameters, lags, costs and timing are
identical to the U.S. model -- nothing is re-tuned for the region.

Switzerland (CHF investor, 100 % in Swiss equities <-> CHF cash):
    equity ....... OECD/FRED Swiss share-price index (monthly average, price only)  + ASSUMED dividend yield
    cash ......... Swiss call-money rate (1972-1999) spliced to 3-month interbank (1999+)
    curve ........ Swiss 10-year government yield minus the Swiss short rate           (native)
    valuation .... U.S. CAPE + U.S. corporate-equity/GDP percentiles                  (SUBSTITUTE)
"""
from __future__ import annotations

import dataclasses as dc
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import analysis as A
from . import metrics as M
from .config import PARAMS, Params
from .data import Raw, _fred
from .engine import run_weights
from .signals import compute_signals


@dataclass(frozen=True)
class RegionSpec:
    id: str
    name: str
    currency: str
    start: str
    dividend_yield: float             # ASSUMED, annual, added to the price index (no free SPI total-return series)
    inputs: tuple                     # (label, source, origin) origin in {"native","substitute","assumption"}


CH = RegionSpec(
    id="ch", name="Switzerland", currency="CHF", start="1975-01", dividend_yield=0.025,
    inputs=(
        ("Equity index", "Swiss share-price index (OECD via FRED), monthly average, price only", "native"),
        ("Dividends", "Assumed constant 2.5 % a year added to the price index (no free total-return series)", "assumption"),
        ("Cash return", "Swiss call-money rate 1972–99, 3-month interbank rate 1999+ (spliced)", "native"),
        ("Yield curve", "Swiss 10-year government yield minus Swiss short rate", "native"),
        ("Valuation: CAPE", "U.S. Shiller CAPE percentile — no free Swiss CAPE exists", "substitute"),
        ("Valuation: Buffett indicator", "U.S. corporate equity ÷ GDP percentile — no free Swiss equivalent", "substitute"),
    ),
)
REGIONS = {"ch": CH}


@dataclass
class RegionInputs:
    px: pd.Series          # price index, monthly average
    short: pd.Series       # % p.a. cash rate
    long: pd.Series        # % p.a. 10y yield


def load_ch_inputs(last: pd.Period) -> RegionInputs:
    px = _fred("SPASTT01CHM661N")
    call, tb = _fred("IRSTCI01CHM156N"), _fred("IR3TIB01CHM156N")
    short = pd.concat([call[call.index < tb.index[0]], tb])
    long = _fred("IRLTLT01CHM156N")
    cut = lambda s: s[s.index <= last]  # noqa: E731
    return RegionInputs(cut(px), cut(short), cut(long))


def truncate_inputs(x: RegionInputs, t: pd.Period) -> RegionInputs:
    return RegionInputs(x.px[x.px.index <= t], x.short[x.short.index <= t], x.long[x.long.index <= t])


def compute_region_signals(x: RegionInputs, us: pd.DataFrame, spec: RegionSpec = CH, p: Params = PARAMS) -> pd.DataFrame:
    """Same three warning flags as the U.S. model; valuation regime borrowed (point-in-time) from the U.S. signals."""
    idx = x.px.index
    df = pd.DataFrame(index=idx)
    df["price"] = x.px
    r_eq = x.px.pct_change() + spec.dividend_yield / 12.0
    df["tr_index"] = (1 + r_eq.fillna(0)).cumprod()
    df["r_eq"] = r_eq
    short = x.short.reindex(idx)
    df["short_rate"] = short
    df["long_yield"] = x.long.reindex(idx)
    df["sma"] = df["price"].rolling(p.sma_months, min_periods=p.sma_months).mean()
    df["below_sma"] = df["price"] < df["sma"]
    cash_idx = (1 + (short / 1200.0).fillna(0)).cumprod()
    df["mom12"] = df["tr_index"] / df["tr_index"].shift(p.mom_months) - 1
    df["cash12"] = cash_idx / cash_idx.shift(p.mom_months) - 1
    ok = df["mom12"].notna() & short.shift(p.mom_months - 1).notna()
    df["neg_mom"] = (df["mom12"] < df["cash12"]) & ok
    df["curve"] = df["long_yield"] - short
    df["curve_inv"] = (df["curve"] < p.curve_inversion) & df["curve"].notna()
    # --- substituted valuation (U.S.) ---
    for c in ("cape", "buffett", "cape_pct", "buffett_pct", "val_score"):
        df[f"us_{c}"] = us[c].reindex(idx)
    regime = pd.Series("fair", index=idx)
    regime[df["us_val_score"] >= p.val_rich] = "rich"
    regime[df["us_val_score"] < p.val_cheap] = "cheap"
    df["regime"] = regime
    df["step"] = regime.map({"cheap": p.step_cheap, "fair": p.step_fair, "rich": p.step_rich})
    flags = df[["below_sma", "neg_mom", "curve_inv"]]
    df["n_flags"] = flags.sum(axis=1)
    df["w_target"] = (p.max_equity - df["step"] * df["n_flags"]).clip(p.min_equity, p.max_equity)
    return df


def region_backtest(sig: pd.DataFrame, p: Params = PARAMS, **kw) -> pd.DataFrame:
    r_eq = sig["r_eq"]
    r_cash = sig["short_rate"] / 1200.0
    sim = run_weights(r_eq, r_cash, sig["w_target"], p.cost_per_trade, **kw)
    bt = sig.join(sim, how="inner")
    bt["r_bh"] = r_eq.reindex(bt.index)
    bt["r_cash"] = r_cash.reindex(bt.index)
    faber = run_weights(r_eq, r_cash, (~sig["below_sma"]).astype(float), p.cost_per_trade)
    bt["r_faber"] = faber["ret"].reindex(bt.index)
    bt["w_faber"] = faber["w_eff"].reindex(bt.index)
    return bt.dropna(subset=["r_cash", "r_bh", "ret", "r_faber"])


def build_region(raw: Raw, us_sig: pd.DataFrame, spec: RegionSpec = CH, p: Params = PARAMS) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = load_ch_inputs(raw.shiller.index[-1])
    sig = compute_region_signals(x, us_sig, spec, p)
    bt = region_backtest(sig, p).loc[spec.start:]
    return sig, bt


def _variant(sig_inputs: RegionInputs, us: pd.DataFrame, spec: RegionSpec, p: Params, a: str) -> dict:
    sg = compute_region_signals(sig_inputs, us, spec, p)
    bt = region_backtest(sg, p).loc[a:]
    m = M.summary(bt["ret"], bt["r_bh"], bt["r_cash"])
    return A._r(dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"], calmar=m["calmar"],
                     up=m["up_capture"], down=m["down_capture"], avg_equity=float(bt["w_eff"].mean()), bh_cagr=M.cagr(bt["r_bh"])))


def region_ablations(raw: Raw, us: pd.DataFrame, spec: RegionSpec, p: Params = PARAMS) -> list[dict]:
    x = load_ch_inputs(raw.shiller.index[-1])
    a = spec.start
    one = dict(step_cheap=1.0, step_fair=1.0, step_rich=1.0)
    rows = [
        ("Bulwark (final)", spec, p),
        ("No valuation tilt (removes the U.S. substitute)", spec, dc.replace(p, step_cheap=1 / 3, step_rich=1 / 3)),
        ("Trend votes only (no yield curve)", spec, dc.replace(p, cut_flags=("below_sma", "neg_mom"), step_cheap=.4, step_fair=.5, step_rich=.6)),
        ("10-month average only (Faber), all-or-nothing", spec, dc.replace(p, **one)),
        ("Dividend assumption 0 % (price only)", dc.replace(spec, dividend_yield=0.0), p),
        ("Dividend assumption 3.5 %", dc.replace(spec, dividend_yield=0.035), p),
    ]
    out = []
    for name, sp, pp in rows:
        if name.startswith("10-month"):
            sg = compute_region_signals(x, us, sp, pp)
            bt = region_backtest(sg, pp).loc[a:]
            m = M.summary(bt["r_faber"], bt["r_bh"], bt["r_cash"])
            v = A._r(dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"], calmar=m["calmar"],
                          up=m["up_capture"], down=m["down_capture"], avg_equity=float(bt["w_faber"].mean()), bh_cagr=M.cagr(bt["r_bh"])))
        else:
            v = _variant(x, us, sp, pp, a)
        out.append(dict(name=name, full=v))
    sg = compute_region_signals(x, us, spec, p)
    bt = region_backtest(sg, p).loc[a:]
    m = M.summary(bt["r_bh"], bt["r_bh"], bt["r_cash"])
    out.append(dict(name="Buy & hold", full=A._r(dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"],
                                                      calmar=m["calmar"], up=1.0, down=1.0, avg_equity=1.0, bh_cagr=m["cagr"]))))
    return out


def region_series(bt: pd.DataFrame) -> dict:
    d = bt
    idx = lambda r: M.equity_curve(r).round(5).tolist()  # noqa: E731
    rr = lambda s, n=3: [None if pd.isna(x) else round(float(x), n) for x in s]  # noqa: E731
    code = d["regime"].map({"cheap": 0, "fair": 1, "rich": 2}).astype(int)
    bits = sum(d[f].astype(int) * (1 << i) for i, f in enumerate(["below_sma", "neg_mom", "curve_inv"]))
    return dict(
        d=[str(i) for i in d.index], bulwark=idx(d["ret"]), buyhold=idx(d["r_bh"]), cash=idx(d["r_cash"]), faber=idx(d["r_faber"]),
        w=rr(d["w_eff"]), wt=rr(d["w_target"]), nf=d["n_flags"].astype(int).tolist(), flags=bits.astype(int).tolist(),
        regime=code.tolist(), price=rr(d["price"], 2), sma=rr(d["sma"], 2), curve=rr(d["curve"], 2),
        us_cape=rr(d["us_cape"], 2), us_buffett=rr(d["us_buffett"], 3),
    )


def region_snapshot(sig: pd.DataFrame, raw: Raw) -> dict:
    t = sig.index[-1]
    r = sig.loc[t]
    f = lambda x, n=4: None if pd.isna(x) else round(float(x), n)  # noqa: E731
    prev9 = float(sig["price"].iloc[-10:-1].mean())
    tr = sig["tr_index"]
    trip_mom = float(tr.iloc[-12] * (1 + r["cash12"]))
    return dict(
        asof=str(t), next_month=str(t + 1), weight=f(r["w_target"], 3), regime=r["regime"], n_flags=int(r["n_flags"]), step=f(r["step"], 3),
        flags=dict(below_sma=bool(r["below_sma"]), neg_mom=bool(r["neg_mom"]), curve_inv=bool(r["curve_inv"])),
        price=f(r["price"], 1), sma=f(r["sma"], 1), price_vs_sma=f(r["price"] / r["sma"] - 1), trip_sma=f(prev9, 1),
        trip_sma_distance=f(prev9 / r["price"] - 1), mom12=f(r["mom12"]), cash12=f(r["cash12"]),
        trip_mom_distance=f(trip_mom / tr.iloc[-1] - 1), curve=f(r["curve"], 2), short_rate=f(r["short_rate"], 2),
        long_yield=f(r["long_yield"], 2), us_cape=f(r["us_cape"], 1), us_cape_pct=f(r["us_cape_pct"], 3),
        us_buffett=f(r["us_buffett"], 3), us_buffett_pct=f(r["us_buffett_pct"], 3), val_score=f(r["us_val_score"], 3),
    )


def build_region_payload(raw: Raw, us_sig: pd.DataFrame, spec: RegionSpec = CH, p: Params = PARAMS) -> dict:
    sig, bt = build_region(raw, us_sig, spec, p)
    first = str(bt.index[0])
    periods = {
        "full": (spec.start, None, f"{spec.start[:4]} – today"),
        "since1990": ("1990-01", None, "1990 –"),
        "since2010": ("2010-01", None, "2010 –"),
        "lost_decades": ("2000-01", "2012-12", "2000 – 2012"),
    }
    bt_f = bt  # benchmarks already attached
    return dict(
        id=spec.id, name=spec.name, currency=spec.currency, generated=str(pd.Timestamp.today().date()), first=first,
        inputs=[dict(label=a, source=b, origin=c) for a, b, c in spec.inputs],
        dividend_yield=spec.dividend_yield,
        snapshot=region_snapshot(sig, raw),
        headline=A.headline(bt_f, periods),
        calendar=A.calendar_years(bt_f.loc[spec.start:]),
        episodes=A.episodes(bt_f),
        rolling10=A.rolling_windows(bt_f, 10, start=spec.start),
        ablations=region_ablations(raw, us_sig, spec, p),
        bootstrap=A.bootstrap(bt_f, start=spec.start),
        turnover_per_year=round(float(bt["turnover"].sum() / (len(bt) / 12)), 3),
        trades_per_year=round(float((bt["w_signal"].diff().abs() > 0.01).sum() / (len(bt) / 12)), 2),
        series=region_series(bt_f),
    )
