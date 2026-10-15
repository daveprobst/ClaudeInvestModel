"""Leak audit for region packs: signals and returns at t must not change when data after t is removed."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from model.data import load_raw
from model.regions import CH, compute_region_signals, load_ch_inputs, region_backtest, truncate_inputs
from model.signals import compute_signals
from model.tests.test_no_lookahead import truncate

COLS = ["price", "sma", "below_sma", "neg_mom", "curve", "curve_inv", "us_val_score", "regime", "n_flags", "w_target"]


@pytest.fixture(scope="module")
def setup():
    raw = load_raw()
    us = compute_signals(raw)
    x = load_ch_inputs(raw.shiller.index[-1])
    sig = compute_region_signals(x, us, CH)
    return raw, us, x, sig, region_backtest(sig)


def test_swiss_signals_only_use_past_data(setup):
    raw, us, x, sig, bt = setup
    rng = np.random.default_rng(3)
    pool = [t for t in sig.index if pd.Period("1976-01") <= t]
    dates = sorted(rng.choice(len(pool), size=14, replace=False))
    for t in [pool[i] for i in dates] + [sig.index[-1], pd.Period("2008-10")]:
        us_t = compute_signals(truncate(raw, t))
        sg = compute_region_signals(truncate_inputs(x, t), us_t, CH)
        for c in COLS:
            a, b = sg.loc[t, c], sig.loc[t, c]
            if isinstance(b, (float, np.floating)):
                if pd.isna(a) and pd.isna(b):
                    continue
                assert a == pytest.approx(b, rel=1e-9, abs=1e-12), f"{c} at {t}"
            else:
                assert a == b, f"{c} at {t}"
        bt_t = region_backtest(sg)
        assert bt_t.loc[t, "ret"] == pytest.approx(bt.loc[t, "ret"], abs=1e-12), t


def test_swiss_substitutes_are_the_us_series(setup):
    _, us, _, sig, _ = setup
    both = pd.concat([sig["us_cape"], us["cape"]], axis=1).dropna()
    assert (both.iloc[:, 0] == both.iloc[:, 1]).all()


def test_region_weights_bounded(setup):
    *_, bt = setup
    assert bt["w_eff"].between(0, 1).all()
