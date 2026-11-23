import numpy as np
import pandas as pd
import pytest

from model.rolling import daily_signals, load_equity, load_rates, simulate, stats
from model.data import load_raw
from model.signals import compute_signals


@pytest.fixture(scope="module")
def inputs():
    return load_equity(), load_rates(), compute_signals(load_raw())


def test_daily_frequency_and_complete_sessions(inputs):
    e, _, _ = inputs
    assert len(e) > 1000
    assert e.index.is_unique and e.index.is_monotonic_increasing
    assert e.index.to_series().diff().dt.days.median() == 1
    assert e.index[-1].date() < pd.Timestamp.now(tz="America/New_York").date()


def test_rolling_windows_and_truncation(inputs):
    e, r, m = inputs
    full = daily_signals(e, r, m)
    for t in e.index[[500, 1000, -1]]:
        part = daily_signals(e.loc[:t], r.loc[:t], m.loc[:t.to_period("M")])
        pd.testing.assert_frame_equal(part, full.loc[:t])
        a, b = simulate(part), simulate(full).loc[:t]
        pd.testing.assert_frame_equal(a, b)
    assert full.fast.iloc[-1] == pytest.approx(e.price.iloc[-21:].mean())
    assert full.slow.iloc[-1] == pytest.approx(e.price.iloc[-210:].mean())


def test_next_close_execution_and_cost():
    idx = pd.bdate_range("2020-01-01", periods=6)
    d = pd.DataFrame({"total_return": [100, 110, 121, 133.1, 146.41, 161.051],
                      "weight": [1, 0, 1, 1, 1, 1], "cash_return": 0.0}, index=idx)
    bt = simulate(d)
    assert bt.effective_weight.iloc[0] == 1
    assert bt.strategy.iloc[0] == pytest.approx(0.1 - 0.001)
    assert bt.effective_weight.iloc[1] == 0
    assert bt.strategy.iloc[1] == pytest.approx(-0.001)


def test_monthly_regime_not_available_before_month_end(inputs):
    e, r, m = inputs
    d = daily_signals(e, r, m)
    for t in d.index[300::300]:
        assert pd.Period(d.loc[t, "valuation_asof"], freq="M") < t.to_period("M")
    assert d.weight.dropna().between(0, 1).all()


def test_drawdown_includes_initial_capital():
    r = pd.Series([-0.1, 0.0], index=pd.bdate_range("2020-01-01", periods=2))
    assert stats(r, r * 0)["max_dd"] == pytest.approx(-0.1)
