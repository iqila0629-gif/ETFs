"""Fetch VIX/TNX OHLC from Yahoo and merge into external_daily copies."""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from http.cookiejar import CookieJar

import pandas as pd

import config


TICKERS = {"VIX": "%5EVIX", "TNX": "%5ETNX"}
PERIOD1 = 1104537600  # 2005-01-01
EXTEND_TO = pd.Timestamp("2026-08-07")

RAW_DIRS = [
    config.EVENT_INPUTS,
    config.ROOT / "最新结果" / "数据" / "数据_原始",
    config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始",
]
EXTERNAL_PATHS = [d / "external_daily.csv" for d in RAW_DIRS]


def fetch_ticker(name: str, ticker: str) -> pd.DataFrame:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={PERIOD1}&period2={int(time.time())}&interval=1d"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/125"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    rows = []
    for i in range(len(ts)):
        def val(arr):
            if i < len(arr) and arr[i] is not None:
                return round(float(arr[i]), 4)
            return None

        rows.append({
            "Date": pd.Timestamp(time.strftime("%Y-%m-%d", time.gmtime(ts[i]))),
            "Open": val(quote.get("open", [])),
            "High": val(quote.get("high", [])),
            "Low": val(quote.get("low", [])),
            "Close": val(quote.get("close", [])),
        })
    df = pd.DataFrame(rows).dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    print(f"{name}: {len(df)} rows, {df['Date'].iloc[0].date()} .. {df['Date'].iloc[-1].date()}")
    return df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    vix = fetch_ticker("VIX", TICKERS["VIX"])
    tnx = fetch_ticker("TNX", TICKERS["TNX"])

    for raw_dir in RAW_DIRS:
        for name, df in (("VIX", vix), ("TNX", tnx)):
            path = raw_dir / f"{name}_historical.csv"
            df.to_csv(path, index=False, date_format="%m/%d/%Y")
            print("saved:", path)

    external = pd.read_csv(
        config.EXTERNAL_DAILY, parse_dates=["Date"]
    ).sort_values("Date").reset_index(drop=True)

    for name, ohlc, close_col in (
        ("VIX", vix, "VIX_Close"),
        ("TNX", tnx, "TNX_Yield"),
    ):
        for suffix in ("Open", "High", "Low"):
            external = external.drop(columns=[f"{name}_{suffix}"], errors="ignore")
        external = external.drop(columns=[f"{name}_Close_yahoo"], errors="ignore")
        o = ohlc.rename(columns={
            "Open": f"{name}_Open",
            "High": f"{name}_High",
            "Low": f"{name}_Low",
            "Close": f"{name}_Close_yahoo",
        })
        external = external.merge(o, on="Date", how="left")
        yahoo_close = f"{name}_Close_yahoo"
        existing = external[close_col]
        diff = (existing - external[yahoo_close]).dropna()
        mismatches = (diff.abs() > 1e-6).sum()
        filled = existing.isna() & external[yahoo_close].notna()
        print(
            f"{name}: existing-vs-yahoo mismatches {int(mismatches)}/{len(diff)}, "
            f"max abs diff {diff.abs().max() if len(diff) else 0:.6f}, "
            f"missing filled {int(filled.sum())}"
        )
        external[close_col] = existing.fillna(external[yahoo_close])
        external = external.drop(columns=[yahoo_close])

    extra_dates = sorted(set(vix["Date"]) & set(tnx["Date"]))
    extra_dates = [d for d in extra_dates if external["Date"].max() < d <= EXTEND_TO]
    if extra_dates:
        extra = pd.DataFrame({"Date": extra_dates})
        extra = extra.merge(vix, on="Date", how="left")
        extra = extra.merge(tnx, on="Date", how="left", suffixes=("", "_tnx"))
        extra = extra.rename(columns={
            "Open": "VIX_Open",
            "High": "VIX_High",
            "Low": "VIX_Low",
            "Close": "VIX_Close",
            "Open_tnx": "TNX_Open",
            "High_tnx": "TNX_High",
            "Low_tnx": "TNX_Low",
            "Close_tnx": "TNX_Yield",
        })
        extra["SPY"] = None
        external = pd.concat([external, extra], ignore_index=True)
        print("extended to:", extra_dates[-1].date(), "added rows:", len(extra))

    external["VIX_Chg%"] = external["VIX_Close"].pct_change() * 100
    external["TNX_ChgBp"] = external["TNX_Yield"].diff() * 100
    external["VIX_5dChg"] = external["VIX_Close"].pct_change(5) * 100
    external["VIX_20dVol"] = external["VIX_Close"].pct_change().rolling(20).std() * 100
    external["VIX_TNX_Ratio"] = external["VIX_Close"] / external["TNX_Yield"]

    columns = [
        "Date", "SPY",
        "VIX_Open", "VIX_High", "VIX_Low", "VIX_Close", "VIX_Chg%",
        "TNX_Open", "TNX_High", "TNX_Low", "TNX_Yield", "TNX_ChgBp",
        "CreditSpread", "JNKSpread", "StkBonCorr", "USDGoldRatio", "SectRotation",
        "VIX_5dChg", "VIX_20dVol", "VIX_TNX_Ratio", "YldCurveProxy",
    ]
    missing = [c for c in columns if c not in external.columns]
    if missing:
        print("missing columns:", missing)
        sys.exit(1)
    external = external[columns].sort_values("Date", ascending=False).reset_index(drop=True)
    external["Date"] = external["Date"].dt.strftime("%m/%d/%Y")

    for path in EXTERNAL_PATHS:
        external.to_csv(path, index=False)
        print("saved:", path, "rows", len(external), "cols", len(external.columns))


if __name__ == "__main__":
    main()
