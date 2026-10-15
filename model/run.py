"""Run the whole pipeline: signals -> backtest -> analysis -> JSON/CSV for the website.

    python -m model.run            # uses the committed raw data
    python -m model.run --fetch    # re-download raw data first
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from . import analysis as A
from .config import FLAG_LABELS, PARAMS
from .data import ROOT, load_raw
from .engine import backtest
from .signals import FLAGS, compute_signals

WEB_DATA = ROOT / "web" / "public" / "data"
OUT = ROOT / "outputs"


def audit() -> dict:
    """Run the leak-audit test-suite and report the result (so the website's claim is always earned)."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "model/tests", "-q", "--no-header", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    return dict(passed=proc.returncode == 0, summary=tail)


def sources(raw) -> list[dict]:
    last = lambda s: str(s.index[-1])[:7]  # noqa: E731
    return [
        dict(name="S&P 500 price, dividends, earnings, CPI (Robert Shiller)", used_for="Total-return series, 10-month average, CAPE",
             last=str(raw.shiller.index[-1]), url="https://shillerdata.com"),
        dict(name="3-month Treasury bill (FRED TB3MS)", used_for="Cash return, yield curve, momentum hurdle", last=last(raw.tb3), url="https://fred.stlouisfed.org/series/TB3MS"),
        dict(name="10-year Treasury yield (FRED GS10 / Shiller)", used_for="Yield curve, credit spread", last=last(raw.gs10), url="https://fred.stlouisfed.org/series/GS10"),
        dict(name="Fed Z.1 nonfinancial corporate equities (NCBEILQ027S)", used_for="Buffett indicator numerator", last=last(raw.z1_equity), url="https://fred.stlouisfed.org/series/NCBEILQ027S"),
        dict(name="Nominal GDP (FRED GDP)", used_for="Buffett indicator denominator", last=last(raw.gdp), url="https://fred.stlouisfed.org/series/GDP"),
        dict(name="Moody's Baa yield (FRED BAA)", used_for="Credit spread (shown, does not cut equity)", last=last(raw.baa), url="https://fred.stlouisfed.org/series/BAA"),
        dict(name="Unemployment rate (FRED UNRATE)", used_for="Sahm rule (shown, does not cut equity)", last=last(raw.unrate), url="https://fred.stlouisfed.org/series/UNRATE"),
        dict(name="OECD share price indices via FRED (8 markets)", used_for="International out-of-sample trend check", last="2026-09", url="https://fred.stlouisfed.org/"),
        dict(name="CBOE VIX, Chicago Fed NFCI, S&P 500 daily (FRED)", used_for="Live context only – not model inputs",
             last=str(raw.sp500_daily.index[-1].date()), url="https://fred.stlouisfed.org/series/VIXCLS"),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--skip-audit", action="store_true")
    args = ap.parse_args()
    if args.fetch:
        from . import fetch
        fetch.main()

    raw = load_raw()
    sig = compute_signals(raw)
    bt = A.with_benchmarks(raw, backtest(raw, sig=sig))

    print("analysis ...")
    model = dict(
        name="Bulwark",
        generated=str(pd.Timestamp.today().date()),
        params={k: v for k, v in dataclasses.asdict(PARAMS).items()},
        flag_labels=FLAG_LABELS,
        snapshot=A.snapshot(raw, sig, bt),
        headline=A.headline(bt),
        calendar=A.calendar_years(bt),
        episodes=A.episodes(bt),
        rolling10=A.rolling_windows(bt, 10),
        flag_diagnostics=A.flag_diagnostics(raw, bt),
        ablations=A.ablations(raw),
        sensitivity=A.sensitivity(raw),
        bootstrap=A.bootstrap(bt),
        international=A.international(raw),
        sources=sources(raw),
        turnover_per_year=round(float(bt.loc["1970":, "turnover"].sum() / (len(bt.loc["1970":]) / 12)), 3),
        trades_per_year=round(float((bt.loc["1970":, "w_signal"].diff().abs() > 0.01).sum() / (len(bt.loc["1970":]) / 12)), 2),
        regime_share=bt.loc["1970":, "regime"].value_counts(normalize=True).round(3).to_dict(),
        flag_share={f: round(float(bt.loc["1970":, f].mean()), 3) for f in FLAGS},
        audit=dict(passed=None, summary="skipped") if args.skip_audit else audit(),
    )
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    (WEB_DATA / "model.json").write_text(json.dumps(model, separators=(",", ":")))
    (WEB_DATA / "series.json").write_text(json.dumps(A.series_export(bt), separators=(",", ":")))
    (OUT / "metrics.json").write_text(json.dumps({k: model[k] for k in ("headline", "episodes", "rolling10", "bootstrap", "audit")}, indent=1))
    cols = ["price", "sma", "below_sma", "neg_mom", "curve_inv", "credit_stress", "sahm", "cape", "cape_pct", "buffett", "buffett_pct",
            "regime", "n_flags", "w_target", "w_eff", "ret", "r_bh", "r_cash", "r_faber"]
    bt.loc["1940":, cols].to_csv(OUT / "monthly_paths.csv", float_format="%.6f")
    print("audit:", model["audit"])
    print("wrote", WEB_DATA / "model.json", "and series.json")


if __name__ == "__main__":
    main()
