# -*- coding: utf-8 -*-
"""Download clean EIP fund daily history from Yahoo v8 chart API.

For each clean target: fetch OHLCV + Adj Close (1998-01-01 .. today, interval=1d)
and save as  01_数据/新项目_基金价格/<规范名>.csv  with Date=YYYY-MM-DD.

Idempotent: existing files with rows>0 are skipped. Retries each symbol twice.
Writes a manifest  eip_download_manifest.csv  (name, symbol, rows, first, last, currency, status).
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

import pandas as pd

import config_eip as config


UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}
SLEEP = 0.4
MAX_RETRIES = 2


def fetch_chart(symbol: str) -> dict:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}"
        f"?period1={config.PERIOD1}&period2={int(time.time())}&interval=1d"
    )
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(url, headers=UA)
    with opener.open(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    meta = result.get("meta", {})
    rows = []
    for i, t in enumerate(ts):
        def val(arr):
            if i < len(arr) and arr[i] is not None:
                return float(arr[i])
            return float("nan")
        rows.append({
            "Date": datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"),
            "Open": val(quote.get("open", [])),
            "High": val(quote.get("high", [])),
            "Low": val(quote.get("low", [])),
            "Close": val(quote.get("close", [])),
            "Volume": val(quote.get("volume", [])),
            "Adj Close": val(adj),
        })
    return {
        "rows": rows,
        "currency": meta.get("currency", ""),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.PRICE_DIR.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    targets = config.load_clean_targets()

    manifest: list[dict] = []
    ok, fail = 0, 0
    for i, (name, symbol) in enumerate(
        zip(targets["name"], targets["symbol"]), start=1
    ):
        safe = "".join(ch for ch in name if ch not in '\\/:*?"<>|')
        out_path = config.PRICE_DIR / f"{safe}.csv"
        if out_path.exists():
            exist = pd.read_csv(out_path)
            if len(exist) > 0:
                manifest.append({
                    "name": name, "symbol": symbol,
                    "rows": len(exist),
                    "first": exist["Date"].iloc[0],
                    "last": exist["Date"].iloc[-1],
                    "currency": "", "status": "exists",
                })
                ok += 1
                print(f"[{i}/{len(targets)}] {name}: exists ({len(exist)} rows)", flush=True)
                continue

        data = None
        err = ""
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                data = fetch_chart(symbol)
                break
            except Exception as e:  # noqa: BLE001
                err = str(e)
                print(f"  {symbol} attempt {attempt} failed: {e}", flush=True)
                time.sleep(2 * attempt)
        if data is None or not data["rows"]:
            manifest.append({
                "name": name, "symbol": symbol, "rows": 0,
                "first": "", "last": "", "currency": "", "status": f"FAIL: {err[:120]}",
            })
            fail += 1
            print(f"[{i}/{len(targets)}] {name}: FAIL {err[:120]}", flush=True)
            time.sleep(SLEEP)
            continue

        df = pd.DataFrame(data["rows"])
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        manifest.append({
            "name": name, "symbol": symbol,
            "rows": len(df), "first": df["Date"].iloc[0], "last": df["Date"].iloc[-1],
            "currency": data["currency"], "status": "ok",
        })
        ok += 1
        print(
            f"[{i}/{len(targets)}] {name}: {len(df)} rows "
            f"{df['Date'].iloc[0]} .. {df['Date'].iloc[-1]} cur={data['currency']}",
            flush=True,
        )
        time.sleep(SLEEP)

    pd.DataFrame(manifest).to_csv(
        config.PROCESSED_DIR / "eip_download_manifest.csv",
        index=False, encoding="utf-8-sig",
    )
    print(f"DONE ok={ok} fail={fail}  manifest saved")


if __name__ == "__main__":
    main()