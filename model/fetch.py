"""Download every raw input the model uses into data/raw/.

All sources are free and public:
  * Robert Shiller's U.S. stock market file (S&P composite price, dividends, earnings, CPI,
    total-return index) -- the official, *current* file from shillerdata.com.
  * FRED (Federal Reserve Bank of St. Louis) CSV endpoints: interest rates, credit yields,
    unemployment, GDP, Fed Z.1 equity market value, VIX, NFCI, OECD share-price indices.

Run:  python -m model.fetch
Raw files are committed to the repo so results are reproducible without network access.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (compatible; CommonSenseShield/1.0; research)"}

FRED = {
    # name: description
    "GS10": "10-year Treasury yield (monthly avg, 1953+)",
    "TB3MS": "3-month Treasury bill rate (monthly avg, 1934+) -- cash return & curve",
    "BAA": "Moody's Baa corporate yield (1919+) -- credit spread",
    "UNRATE": "Civilian unemployment rate (1948+) -- Sahm rule",
    "GDP": "Nominal GDP, SAAR (quarterly, 1947+) -- Buffett indicator denominator",
    "NCBEILQ027S": "Nonfinancial corporate equities, market value (Fed Z.1, quarterly, 1945+) -- Buffett numerator",
    "VIXCLS": "CBOE VIX (daily, 1990+) -- live context only, not used by the model",
    "NFCI": "Chicago Fed NFCI (weekly, 1971+) -- live context only, not used by the model",
    "SP500": "S&P 500 daily close (last ~10y) -- live context only",
}
# OECD share-price indices (monthly average, local currency, price only) -- international trend check
OECD = {
    "SPASTT01USM661N": "United States",
    "SPASTT01DEM661N": "Germany",
    "SPASTT01CHM661N": "Switzerland",
    "SPASTT01JPM661N": "Japan",
    "SPASTT01GBM661N": "United Kingdom",
    "SPASTT01FRM661N": "France",
    "SPASTT01CAM661N": "Canada",
    "SPASTT01AUM661N": "Australia",
}


def _get(url: str, tries: int = 4) -> bytes:
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"failed to download {url}: {last}")


def fetch_fred(series: str) -> None:
    data = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    if data.lstrip().startswith(b"<"):
        raise RuntimeError(f"FRED returned HTML for {series}")
    (RAW / f"{series}.csv").write_bytes(data)
    print(f"  {series:<18} {len(data.splitlines()) - 1:>6} rows")


def fetch_shiller() -> None:
    page = _get("https://shillerdata.com/").decode("utf-8", "ignore")
    m = re.search(r'href="(//img1\.wsimg\.com/blobby/go/[^"]*?/ie_data\.xls[^"]*)"', page)
    if not m:
        raise RuntimeError("could not find ie_data.xls link on shillerdata.com")
    data = _get("https:" + m.group(1).replace("&amp;", "&"))
    (RAW / "shiller_ie_data.xls").write_bytes(data)
    print(f"  shiller_ie_data.xls {len(data) / 1e6:.2f} MB")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    print("Shiller:")
    fetch_shiller()
    print("FRED:")
    for s in list(FRED) + list(OECD):
        fetch_fred(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
