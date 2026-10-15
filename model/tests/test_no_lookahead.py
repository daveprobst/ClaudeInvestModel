"""Leak audit.

For many dates ``t`` we hand the model ONLY the data that existed up to ``t`` (every series truncated),
recompute everything from scratch, and require that the signals at ``t`` -- and the portfolio return at
``t`` -- are identical to what the full-history run produced. If any computation peeked at the future
(centered window, full-sample percentile, un-lagged release, ...) this test fails.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from model.data import Raw, load_raw
from model.engine import backtest
from model.signals import FLAGS, compute_signals, expanding_pct

SIGNAL_COLS = ["price", "sma", "below_sma", "neg_mom", "curve", "curve_inv", "credit_spread", "credit_pct",
               "credit_stress", "sahm_gap", "sahm", "cape", "buffett", "cape_pct", "buffett_pct", "val_score",
               "regime", "n_flags", "w_target"]


def truncate(raw: Raw, t: pd.Period) -> Raw:
    cut = lambda s: s[s.index <= t]  # noqa: E731
    ts = t.to_timestamp(how="end")
    cutd = lambda s: s[s.index <= ts]  # noqa: E731
    return dataclasses.replace(
        raw, shiller=raw.shiller[raw.shiller.index <= t], gs10=cut(raw.gs10), tb3=cut(raw.tb3), baa=cut(raw.baa),
        unrate=cut(raw.unrate), gdp=cut(raw.gdp), z1_equity=cut(raw.z1_equity),
        vix=cutd(raw.vix), nfci=cutd(raw.nfci), sp500_daily=cutd(raw.sp500_daily))


@pytest.fixture(scope="module")
def raw() -> Raw:
    return load_raw()


@pytest.fixture(scope="module")
def full(raw):
    return compute_signals(raw), backtest(raw)


def _sample_dates(index: pd.PeriodIndex, n: int = 24) -> list[pd.Period]:
    rng = np.random.default_rng(7)
    pool = [t for t in index if pd.Period("1962-01") <= t <= index[-1]]
    picks = sorted(rng.choice(len(pool), size=n, replace=False))
    return [pool[i] for i in picks] + [index[-1], pd.Period("2008-10"), pd.Period("2020-03")]


def test_signals_use_only_past_data(raw, full):
    sig_full, _ = full
    for t in _sample_dates(sig_full.index):
        sig_t = compute_signals(truncate(raw, t))
        a, b = sig_t.loc[t, SIGNAL_COLS], sig_full.loc[t, SIGNAL_COLS]
        for c in SIGNAL_COLS:
            x, y = a[c], b[c]
            if isinstance(y, (float, np.floating)) and (pd.isna(x) and pd.isna(y)):
                continue
            if isinstance(y, (float, np.floating)):
                assert x == pytest.approx(y, rel=1e-9, abs=1e-12), f"{c} differs at {t}: {x} vs {y}"
            else:
                assert x == y, f"{c} differs at {t}: {x} vs {y}"


def test_portfolio_return_uses_only_past_data(raw, full):
    _, bt_full = full
    for t in _sample_dates(bt_full.index, n=12):
        bt_t = backtest(truncate(raw, t))
        assert bt_t.loc[t, "ret"] == pytest.approx(bt_full.loc[t, "ret"], rel=1e-9, abs=1e-12), t
        assert bt_t.loc[t, "w_eff"] == pytest.approx(bt_full.loc[t, "w_eff"], abs=1e-12), t


def test_future_cannot_change_past_weights(raw, full):
    """Corrupt every observation after t with noise: no weight up to t may move."""
    sig_full, _ = full
    t = pd.Period("1999-06")
    bad = dataclasses.replace(raw)
    sh = raw.shiller.copy()
    fut = sh.index > t
    rng = np.random.default_rng(1)
    for c in ["P", "E", "CPI", "tr_index"]:
        sh.loc[fut, c] = sh.loc[fut, c] * rng.uniform(0.3, 3, fut.sum())
    bad = dataclasses.replace(raw, shiller=sh)
    sig_bad = compute_signals(bad)
    past = sig_full.index <= t
    pd.testing.assert_series_equal(sig_full.loc[past, "w_target"], sig_bad.loc[past, "w_target"])


def test_expanding_percentile_is_causal():
    x = pd.Series([1.0, 5.0, 3.0, 4.0, 2.0, 10.0, 0.5])
    p = expanding_pct(x, 3)
    assert np.isnan(p.iloc[0]) and np.isnan(p.iloc[1])
    assert p.iloc[2] == pytest.approx(2 / 3)           # 3 within [1,5,3]
    assert p.iloc[5] == 1.0                            # new high
    assert p.iloc[6] == pytest.approx(1 / 7)           # new low
    # appending data never changes earlier values
    q = expanding_pct(x.iloc[:5], 3)
    pd.testing.assert_series_equal(q, p.iloc[:5])


def test_weights_in_bounds_and_flags_boolean(full):
    sig, bt = full
    assert sig["w_target"].dropna().between(0, 1).all()
    assert bt["w_eff"].between(0, 1).all()
    for f in FLAGS:
        assert sig[f].dtype == bool


def test_cape_tracks_published_series(raw, full):
    sig, _ = full
    both = pd.concat([sig["cape"], raw.shiller["CAPE_shiller"]], axis=1).dropna().loc["1950":]
    ratio = both.iloc[:, 0] / both.iloc[:, 1]
    assert abs(ratio.mean() - 1) < 0.03       # point-in-time CAPE ~ Shiller's (slightly stale earnings)
    assert both.corr().iloc[0, 1] > 0.99


def test_known_history_sanity(full):
    sig, _ = full
    # Dec-2008: deep bear, trend flags on; Jun-2026: bull market, nothing flagged
    assert sig.loc["2008-12", "below_sma"] and sig.loc["2008-12", "neg_mom"]
    assert sig.loc["2008-12", "w_target"] <= 0.35
    assert not sig.loc["2026-06", "below_sma"]
