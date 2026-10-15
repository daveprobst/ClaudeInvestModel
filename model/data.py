"""Load raw files into clean monthly pandas objects (PeriodIndex, freq='M').

Convention: a value stored at period ``t`` is the value *for* month ``t``. Publication lags are NOT
applied here -- they are applied explicitly (and testably) in ``signals.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def _fred(name: str) -> pd.Series:
    df = pd.read_csv(RAW / f"{name}.csv")
    df.columns = ["date", "v"]
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    s = df.dropna().set_index(pd.to_datetime(df.dropna()["date"]))["v"]
    s.index = s.index.to_period("M")
    return s[~s.index.duplicated(keep="last")].astype(float)


def _fred_quarterly(name: str) -> pd.Series:
    """Quarterly FRED series dated at quarter *start*; re-index by quarter-end month."""
    df = pd.read_csv(RAW / f"{name}.csv")
    df.columns = ["date", "v"]
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df = df.dropna()
    idx = pd.to_datetime(df["date"]).dt.to_period("Q").dt.asfreq("M", how="end")
    return pd.Series(df["v"].values, index=idx).astype(float)


def _shiller(today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Robert Shiller's monthly U.S. file. Prices are monthly averages of daily closes."""
    raw = pd.read_excel(RAW / "shiller_ie_data.xls", sheet_name="Data", header=None).iloc[8:]
    raw = raw[pd.to_numeric(raw[0], errors="coerce").notna()]
    d = raw[0].astype(float)
    year = np.floor(d + 1e-9).astype(int)
    month = np.round((d - year) * 100).astype(int)
    idx = pd.PeriodIndex.from_fields(year=year.values, month=month.values, freq="M")
    cols = {1: "P", 2: "D", 3: "E", 4: "CPI", 6: "GS10", 9: "real_tr_price", 12: "CAPE_shiller",
            17: "bond_tr_growth"}
    out = pd.DataFrame({n: pd.to_numeric(raw[c], errors="coerce").values for c, n in cols.items()}, index=idx)
    out = out[~out.index.duplicated(keep="last")]
    # The newest row in the file is an early-month reading ("Oct price is Oct 2nd close"); only keep
    # months that are complete as of "today" so the model never trades on a half-month average.
    today = pd.Timestamp.today().normalize() if today is None else today
    last_complete = (today.to_period("M") - 1)
    out = out[out.index <= last_complete]
    # nominal total-return index: real TR price (dividends reinvested) re-inflated by CPI
    out["tr_index"] = out["real_tr_price"] * out["CPI"]
    out["tr_index"] /= out["tr_index"].iloc[0]
    return out


@dataclass
class Raw:
    shiller: pd.DataFrame       # P, D, E, CPI, GS10, tr_index, CAPE_shiller, bond_tr_growth
    gs10: pd.Series             # % (FRED, 1953+), falls back to Shiller's long rate before
    tb3: pd.Series             # % 3-month bill (1934+)
    baa: pd.Series              # % Moody's Baa (1919+)
    unrate: pd.Series           # % unemployment (1948+)
    gdp: pd.Series              # $bn SAAR, indexed by quarter-end month
    z1_equity: pd.Series        # $m nonfinancial corporate equities at market value, quarter-end month
    vix: pd.Series              # daily
    nfci: pd.Series             # weekly
    sp500_daily: pd.Series      # daily


def load_raw(today: pd.Timestamp | None = None) -> Raw:
    sh = _shiller(today)
    gs10 = _fred("GS10")
    gs10 = pd.concat([sh["GS10"][sh["GS10"].index < gs10.index[0]], gs10])  # long yield before 1953
    gs10 = gs10[gs10.index <= sh.index[-1]]

    def _daily(name: str) -> pd.Series:
        df = pd.read_csv(RAW / f"{name}.csv")
        df.columns = ["date", "v"]
        df["v"] = pd.to_numeric(df["v"], errors="coerce")
        df = df.dropna()
        return pd.Series(df["v"].values, index=pd.to_datetime(df["date"]))

    return Raw(
        shiller=sh,
        gs10=gs10,
        tb3=_fred("TB3MS"),
        baa=_fred("BAA"),
        unrate=_fred("UNRATE"),
        gdp=_fred_quarterly("GDP"),
        z1_equity=_fred_quarterly("NCBEILQ027S"),
        vix=_daily("VIXCLS"),
        nfci=_daily("NFCI"),
        sp500_daily=_daily("SP500"),
    )


def load_oecd() -> dict[str, pd.Series]:
    names = {"SPASTT01USM661N": "United States", "SPASTT01DEM661N": "Germany", "SPASTT01CHM661N": "Switzerland",
             "SPASTT01JPM661N": "Japan", "SPASTT01GBM661N": "United Kingdom", "SPASTT01FRM661N": "France",
             "SPASTT01CAM661N": "Canada", "SPASTT01AUM661N": "Australia"}
    return {n: _fred(k) for k, n in names.items()}
