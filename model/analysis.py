"""Everything we *report*. Nothing here selects parameters -- grids only show how results move when a
pre-set value is nudged."""
from __future__ import annotations

import dataclasses as dc
import itertools

import numpy as np
import pandas as pd

from . import metrics as M
from .config import PARAMS, Params
from .data import Raw, load_oecd
from .engine import backtest, run_weights
from .signals import FLAGS, compute_signals

PERIODS = {
    "full": ("1970-01", None, "1970 – today"),
    "holdout": ("1940-01", "1969-12", "1940 – 1969 (holdout)"),
    "since1990": ("1990-01", None, "1990 – today"),
    "since2010": ("2010-01", None, "2010 – today"),
    "lost_decades": ("2000-01", "2012-12", "2000 – 2012"),
}


# --------------------------------------------------------------------------------------------------
# benchmarks
# --------------------------------------------------------------------------------------------------
def with_benchmarks(raw: Raw, bt: pd.DataFrame, p: Params = PARAMS) -> pd.DataFrame:
    """Add: Faber 10-month rule alone, and a static mix with the same average equity as Bulwark."""
    out = bt.copy()
    r_eq = bt["tr_index"].pct_change()
    faber_w = (~bt["below_sma"]).astype(float)
    fb = run_weights(r_eq, bt["r_cash"].reindex(r_eq.index), faber_w, p.cost_per_trade)
    out["r_faber"] = fb["ret"].reindex(out.index)
    out["w_faber"] = fb["w_eff"].reindex(out.index)
    return out


def static_mix(bt: pd.DataFrame, a: str, b: str | None) -> pd.Series:
    d = bt.loc[a:b] if b else bt.loc[a:]
    w = d["w_eff"].mean()
    return w * d["r_bh"] + (1 - w) * d["r_cash"]


# --------------------------------------------------------------------------------------------------
# headline tables
# --------------------------------------------------------------------------------------------------
def headline(bt: pd.DataFrame, periods: dict | None = None) -> dict:
    out = {}
    for key, (a, b, label) in (periods or PERIODS).items():
        d = bt.loc[a:b] if b else bt.loc[a:]
        rows = {}
        defs = {"bulwark": d["ret"], "buyhold": d["r_bh"], "cash": d["r_cash"], "faber": d["r_faber"],
                "static": static_mix(bt, a, b)}
        for name, r in defs.items():
            m = M.summary(r, d["r_bh"], d["r_cash"])
            m["avg_equity"] = float({"bulwark": d["w_eff"].mean(), "buyhold": 1.0, "cash": 0.0,
                                     "faber": d["w_faber"].mean(), "static": d["w_eff"].mean()}[name])
            rows[name] = _clean(m)
        out[key] = dict(label=label, start=str(d.index[0]), end=str(d.index[-1]), months=len(d), metrics=rows)
    return out


def _clean(d: dict) -> dict:
    return {k: (None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else round(float(v), 5)) for k, v in d.items()}


def calendar_years(bt: pd.DataFrame) -> list[dict]:
    d = bt.loc["1970":]
    g = lambda c: d[c].groupby(d.index.year).apply(lambda x: (1 + x).prod() - 1)  # noqa: E731
    yr = pd.DataFrame({"bulwark": g("ret"), "buyhold": g("r_bh"), "cash": g("r_cash")})
    yr["avg_equity"] = d["w_eff"].groupby(d.index.year).mean()
    return [dict(year=int(y), **{k: round(float(v), 4) for k, v in row.items()}) for y, row in yr.iterrows()]


# --------------------------------------------------------------------------------------------------
# drawdown episodes (identified on buy&hold, then judged for every strategy)
# --------------------------------------------------------------------------------------------------
def episodes(bt: pd.DataFrame, threshold: float = 0.15) -> list[dict]:
    rows = []
    bh = bt["r_bh"]
    curves = {k: M.equity_curve(bt[c]) for k, c in [("bulwark", "ret"), ("buyhold", "r_bh"), ("faber", "r_faber")]}
    for e in M.drawdown_episodes(bh.loc["1940":], threshold).itertuples():
        pk, tr, rec = e.peak, e.trough, e.recovery
        end = rec if rec is not None else bh.index[-1]
        row = dict(peak=str(pk), trough=str(tr), recovery=None if rec is None else str(rec), depth_bh=round(e.depth, 4))
        for k, c in curves.items():
            seg = c.loc[pk:tr]
            row[f"{k}_peak_to_trough"] = round(float(seg.iloc[-1] / seg.iloc[0] - 1), 4)
            row[f"{k}_max_dd"] = round(float((seg / seg.iloc[0]).min() - 1), 4)
            full = c.loc[pk:end]
            row[f"{k}_full_cycle"] = round(float(full.iloc[-1] / full.iloc[0] - 1), 4)
        row["bulwark_equity_at_trough"] = round(float(bt["w_eff"].loc[tr]), 3)
        row["months_peak_to_trough"] = int((tr - pk).n)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------------------------------
# rolling windows
# --------------------------------------------------------------------------------------------------
def rolling_windows(bt: pd.DataFrame, years: int = 10, start: str = "1970-01") -> dict:
    d = bt.loc[start:]
    n = years * 12
    cs = {k: M.equity_curve(d[c]) for k, c in [("bulwark", "ret"), ("buyhold", "r_bh")]}
    ann = {k: (v.shift(-n) / v) ** (1 / years) - 1 for k, v in cs.items()}
    df = pd.DataFrame(ann).dropna()
    diff = df["bulwark"] - df["buyhold"]
    mdd = {}
    for k, c in [("bulwark", "ret"), ("buyhold", "r_bh")]:
        r = d[c]
        mdd[k] = pd.Series([M.max_dd(r.iloc[i:i + n]) for i in range(len(df))], index=df.index)
    return dict(
        years=years, windows=len(df),
        share_bulwark_ahead=round(float((diff > 0).mean()), 4),
        share_within_1pt=round(float((diff > -0.01).mean()), 4),
        median_diff=round(float(diff.median()), 4), worst_diff=round(float(diff.min()), 4), best_diff=round(float(diff.max()), 4),
        worst_bulwark=round(float(df["bulwark"].min()), 4), worst_buyhold=round(float(df["buyhold"].min()), 4),
        median_bulwark=round(float(df["bulwark"].median()), 4), median_buyhold=round(float(df["buyhold"].median()), 4),
        median_dd_bulwark=round(float(mdd["bulwark"].median()), 4), median_dd_buyhold=round(float(mdd["buyhold"].median()), 4),
        series=[dict(d=str(i), b=round(float(r.bulwark), 4), h=round(float(r.buyhold), 4)) for i, r in df.iloc[::3].iterrows()],
    )


# --------------------------------------------------------------------------------------------------
# what each flag knows (used to justify which flags cut equity)
# --------------------------------------------------------------------------------------------------
def flag_diagnostics(raw: Raw, bt: pd.DataFrame) -> list[dict]:
    eq = raw.shiller["tr_index"].pct_change()
    cash = raw.tb3.reindex(bt.index) / 1200
    fwd = (eq - cash.reindex(eq.index)).shift(-2)          # month t+2: its window starts after the close of t
    rows = []
    for per, (a, b) in {"1970–2026": ("1970-01", "2026-06"), "1940–1969 (holdout)": ("1940-01", "1969-12")}.items():
        d = bt.loc[a:b]
        f = fwd.reindex(d.index)
        for flag in FLAGS:
            on = d[flag].astype(bool)
            if on.sum() < 12 or (~on).sum() < 12:
                rows.append(dict(period=per, flag=flag, share_on=round(float(on.mean()), 3), xs_on=None, xs_off=None))
                continue
            rows.append(dict(period=per, flag=flag, share_on=round(float(on.mean()), 3),
                             xs_on=round(float(1200 * f[on].mean()), 2), xs_off=round(float(1200 * f[~on].mean()), 2)))
    return rows


# --------------------------------------------------------------------------------------------------
# variants: ablations & sensitivity
# --------------------------------------------------------------------------------------------------
def _run(raw: Raw, p: Params, a: str, b: str | None, **kw) -> dict:
    bt = backtest(raw, p, **kw)
    d = bt.loc[a:b] if b else bt.loc[a:]
    m = M.summary(d["ret"], d["r_bh"], d["r_cash"])
    return dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"], calmar=m["calmar"],
                up=m["up_capture"], down=m["down_capture"], avg_equity=float(d["w_eff"].mean()))


def _r(d: dict) -> dict:
    return {k: round(float(v), 4) for k, v in d.items()}


def ablations(raw: Raw) -> list[dict]:
    one = dict(step_cheap=1.0, step_fair=1.0, step_rich=1.0)
    half = dict(step_cheap=.5, step_fair=.5, step_rich=.5)
    V = [
        ("Bulwark (final)", PARAMS),
        ("No valuation tilt", dc.replace(PARAMS, step_cheap=1 / 3, step_rich=1 / 3)),
        ("Trend votes only (no yield curve)", dc.replace(PARAMS, cut_flags=("below_sma", "neg_mom"), step_cheap=.4, step_fair=.5, step_rich=.6)),
        ("10-month average only (Faber), all-or-nothing", dc.replace(PARAMS, cut_flags=("below_sma",), **one)),
        ("12-month momentum only, all-or-nothing", dc.replace(PARAMS, cut_flags=("neg_mom",), **one)),
        ("Yield curve only, all-or-nothing", dc.replace(PARAMS, cut_flags=("curve_inv",), **one)),
        ("10-month avg + curve (2 equal votes)", dc.replace(PARAMS, cut_flags=("below_sma", "curve_inv"), **half)),
        ("Add credit & Sahm votes (v0 – rejected)", dc.replace(PARAMS, cut_flags=("below_sma", "neg_mom", "curve_inv", "credit_stress", "sahm"),
                                                               step_cheap=.15, step_fair=.2, step_rich=.25)),
        ("Yield curve counts only if price agrees (v2)", dc.replace(PARAMS, curve_needs_trend=True)),
    ]
    rows = []
    for name, p in V:
        rows.append(dict(name=name, full=_r(_run(raw, p, "1970-01", None)), holdout=_r(_run(raw, p, "1940-01", "1969-12"))))
    bt = backtest(raw)

    def bh(a: str, b: str | None) -> dict:
        d = bt.loc[a:b] if b else bt.loc[a:]
        m = M.summary(d["r_bh"], d["r_bh"], d["r_cash"])
        return _r(dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"], calmar=m["calmar"],
                       up=1.0, down=1.0, avg_equity=1.0))

    rows.append(dict(name="Buy & hold", full=bh("1970-01", None), holdout=bh("1940-01", "1969-12")))
    return rows


def sensitivity(raw: Raw) -> dict:
    out: dict = {}
    # 1) lookback lengths -------------------------------------------------------------------------
    grid = []
    for s, m in itertools.product((6, 8, 10, 12), (6, 9, 12)):
        r = _r(_run(raw, dc.replace(PARAMS, sma_months=s, mom_months=m), "1970-01", None))
        grid.append(dict(sma=s, mom=m, chosen=(s == 10 and m == 12), **r))
    out["lookbacks"] = grid
    # 2) valuation thresholds ---------------------------------------------------------------------
    grid = []
    for rich, cheap in itertools.product((0.7, 0.8, 0.9), (0.4, 0.5, 0.6)):
        r = _r(_run(raw, dc.replace(PARAMS, val_rich=rich, val_cheap=cheap), "1970-01", None))
        grid.append(dict(rich=rich, cheap=cheap, chosen=(rich == 0.8 and cheap == 0.5), **r))
    out["valuation"] = grid
    # 3) step size (how much each warning removes) -------------------------------------------------
    grid = []
    for fair in (0.25, 1 / 3, 0.5):
        for tilt, label in ((0, "no valuation tilt"), (1, "tilt (cheap ×0.75, rich ×1.2)")):
            k = (0.75, 1.2) if tilt else (1.0, 1.0)
            p = dc.replace(PARAMS, step_fair=fair, step_cheap=fair * k[0], step_rich=min(1.0, fair * k[1]))
            r = _r(_run(raw, p, "1970-01", None))
            grid.append(dict(step=round(fair, 3), tilt=label, chosen=(abs(fair - 1 / 3) < 1e-9 and tilt == 1), **r))
    out["steps"] = grid
    # 4) frictions, timing, defensive asset, sample start -------------------------------------------
    rows = []
    for c in (0.0, 0.001, 0.0025, 0.005):
        rows.append(dict(group="Trading cost per trade", label=f"{c * 100:.2f}%", chosen=c == 0.001,
                         **_r(_run(raw, dc.replace(PARAMS, cost_per_trade=c), "1970-01", None))))
    for mode, lab in (("half", "Trade at month-end close (baseline)"), ("full", "Act one full month later")):
        rows.append(dict(group="Execution timing", label=lab, chosen=mode == "half", **_r(_run(raw, PARAMS, "1970-01", None, lag_mode=mode))))
    bond = raw.shiller["bond_tr_growth"] - 1
    bt = backtest(raw)
    r_eq = bt["tr_index"].pct_change()
    alt = run_weights(r_eq, bt["r_cash"], bt["w_target"], PARAMS.cost_per_trade, r_alt=bond.reindex(r_eq.index))
    d = bt.join(alt[["ret"]].rename(columns={"ret": "ret_bond"})).loc["1970-01":]
    m = M.summary(d["ret_bond"], d["r_bh"], d["r_cash"])
    rows.append(dict(group="Defensive asset", label="3-month T-bills (baseline)", chosen=True, **_r(_run(raw, PARAMS, "1970-01", None))))
    rows.append(dict(group="Defensive asset", label="10-year Treasuries", chosen=False,
                     **_r(dict(cagr=m["cagr"], max_dd=m["max_dd"], sharpe=m["sharpe"], ulcer=m["ulcer"], calmar=m["calmar"],
                               up=m["up_capture"], down=m["down_capture"], avg_equity=float(d["w_eff"].mean())))))
    for mh in (120, 240, 360):
        rows.append(dict(group="Percentile history needed", label=f"{mh // 12} years", chosen=mh == 240,
                         **_r(_run(raw, dc.replace(PARAMS, pct_min_history=mh), "1970-01", None))))
    for y in ("1950-01", "1960-01", "1970-01", "1980-01", "1990-01", "2000-01"):
        rows.append(dict(group="Sample start", label=y[:4], chosen=y == "1970-01", **_r(_run(raw, PARAMS, y, None))))
    out["other"] = rows
    return out


# --------------------------------------------------------------------------------------------------
# block bootstrap: how likely is the improvement to be luck?
# --------------------------------------------------------------------------------------------------
def bootstrap(bt: pd.DataFrame, start: str = "1970-01", draws: int = 3000, block: int = 12, seed: int = 11) -> dict:
    d = bt.loc[start:]
    s, b, c = d["ret"].to_numpy(), d["r_bh"].to_numpy(), d["r_cash"].to_numpy()
    n = len(s)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(draws, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(draws, -1)[:, :n]
    S, B, C = s[idx], b[idx], c[idx]

    def cg(x):
        return np.prod(1 + x, axis=1) ** (12 / n) - 1

    def mdd(x):
        cv = np.cumprod(1 + x, axis=1)
        return (cv / np.maximum.accumulate(cv, axis=1) - 1).min(axis=1)

    def shp(x):
        e = x - C
        return e.mean(axis=1) / e.std(axis=1) * np.sqrt(12)

    cd, dd, sd = cg(S) - cg(B), mdd(S) - mdd(B), shp(S) - shp(B)
    q = lambda a: [round(float(np.quantile(a, k)), 4) for k in (0.05, 0.5, 0.95)]  # noqa: E731
    return dict(draws=draws, block_months=block, cagr_diff_q=q(cd), maxdd_diff_q=q(dd), sharpe_diff_q=q(sd),
                p_sharpe_better=round(float((sd > 0).mean()), 4), p_maxdd_better=round(float((dd > 0).mean()), 4),
                p_cagr_within_1pt=round(float((cd > -0.01).mean()), 4), p_cagr_better=round(float((cd > 0).mean()), 4))


# --------------------------------------------------------------------------------------------------
# international check: trend pillar only, 8 markets the model was never designed on
# --------------------------------------------------------------------------------------------------
def international(raw: Raw, p: Params = PARAMS) -> list[dict]:
    rows = []
    for name, px in load_oecd().items():
        px = px[px.index <= raw.shiller.index[-1]]
        sma = px.rolling(p.sma_months).mean()
        below = px < sma
        neg = px.pct_change(p.mom_months) < 0                      # absolute momentum, cash assumed 0%
        w = (1 - 0.5 * (below.astype(int) + neg.astype(int)))       # trend votes only, 50% each
        w_faber = (~below).astype(float)
        r_eq = px.pct_change()
        zero = pd.Series(0.0, index=r_eq.index)
        a = run_weights(r_eq, zero, w, p.cost_per_trade)["ret"]
        f = run_weights(r_eq, zero, w_faber, p.cost_per_trade)["ret"]
        d = pd.concat([a, f, r_eq], axis=1, keys=["a", "f", "bh"]).dropna().loc["1960-01":]
        if len(d) < 240:
            continue
        rows.append(dict(
            market=name, start=str(d.index[0]), months=len(d),
            bh_cagr=round(M.cagr(d.bh), 4), bh_dd=round(M.max_dd(d.bh), 4),
            trend_cagr=round(M.cagr(d.a), 4), trend_dd=round(M.max_dd(d.a), 4),
            faber_cagr=round(M.cagr(d.f), 4), faber_dd=round(M.max_dd(d.f), 4),
            equity_share=round(float(w.reindex(d.index).mean()), 3)))
    return rows


# --------------------------------------------------------------------------------------------------
# live snapshot
# --------------------------------------------------------------------------------------------------
def snapshot(raw: Raw, sig: pd.DataFrame, bt: pd.DataFrame) -> dict:
    t = sig.index[-1]
    row = sig.loc[t]
    sh = raw.shiller
    prev9 = sh["P"].iloc[-10:-1].mean() if len(sh) >= 10 else np.nan      # trip level for next month's average
    trip_sma = float(prev9)
    cash12_prev = float(row["cash12"])
    tr = sh["tr_index"]
    trip_mom_tr = float(tr.iloc[-12] * (1 + cash12_prev)) if len(tr) >= 12 else np.nan
    f = lambda x, n=4: None if pd.isna(x) else round(float(x), n)  # noqa: E731
    live = {}
    if len(raw.sp500_daily):
        live.update(sp500=f(raw.sp500_daily.iloc[-1], 2), sp500_date=str(raw.sp500_daily.index[-1].date()))
    if len(raw.vix):
        live.update(vix=f(raw.vix.iloc[-1], 2), vix_date=str(raw.vix.index[-1].date()))
    if len(raw.nfci):
        live.update(nfci=f(raw.nfci.iloc[-1], 3), nfci_date=str(raw.nfci.index[-1].date()))
    return dict(
        asof=str(t), next_month=str(t + 1),
        weight=f(row["w_target"], 3), regime=row["regime"], n_flags=int(row["n_flags"]), step=f(row["step"], 3),
        flags={k: bool(row[k]) for k in FLAGS},
        price=f(row["price"], 1), sma=f(row["sma"], 1), price_vs_sma=f(row["price"] / row["sma"] - 1),
        trip_sma=f(trip_sma, 1), trip_sma_distance=f(trip_sma / row["price"] - 1),
        mom12=f(row["mom12"]), cash12=f(row["cash12"]), trip_mom_distance=f(trip_mom_tr / tr.iloc[-1] - 1),
        curve=f(row["curve"], 2), credit_spread=f(row["credit_spread"], 2), credit_pct=f(row["credit_pct"], 3),
        sahm_gap=f(row["sahm_gap"], 2),
        cape=f(row["cape"], 1), cape_pct=f(row["cape_pct"], 3), cape_shiller=f(sh["CAPE_shiller"].iloc[-1], 1),
        buffett=f(row["buffett"], 3), buffett_pct=f(row["buffett_pct"], 3), val_score=f(row["val_score"], 3),
        live=live,
        cape_median=f(sig["cape"].median(), 1), buffett_median=f(sig["buffett"].median(), 3),
    )


def series_export(bt: pd.DataFrame, start: str = "1940-01") -> dict:
    d = bt.loc[start:]
    idx = lambda r: M.equity_curve(r).round(5).tolist()  # noqa: E731
    code = d["regime"].map({"cheap": 0, "fair": 1, "rich": 2}).astype(int)
    bits = sum(d[f].astype(int) * (1 << i) for i, f in enumerate(FLAGS))
    rr = lambda s, n=3: [None if pd.isna(x) else round(float(x), n) for x in s]  # noqa: E731
    return dict(
        d=[str(i) for i in d.index],
        bulwark=idx(d["ret"]), buyhold=idx(d["r_bh"]), cash=idx(d["r_cash"]), faber=idx(d["r_faber"]),
        w=rr(d["w_eff"]), wt=rr(d["w_target"]), nf=d["n_flags"].astype(int).tolist(), flags=bits.astype(int).tolist(),
        regime=code.tolist(), cape=rr(d["cape"], 2), buffett=rr(d["buffett"], 3), cape_pct=rr(d["cape_pct"]),
        buffett_pct=rr(d["buffett_pct"]), price=rr(d["price"], 2), sma=rr(d["sma"], 2), curve=rr(d["curve"], 2),
        credit=rr(d["credit_spread"], 2), sahm=rr(d["sahm_gap"], 2),
    )
