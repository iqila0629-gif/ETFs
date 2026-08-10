"""Download original 19 ETF daily history from Yahoo v8 chart API."""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request
from http.cookiejar import CookieJar

import pandas as pd

import config


ORIGINAL19 = [
    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP", "SLV",
    "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
]
OUT_DIR = config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始" / "etfs"
PERIOD1 = 820454400  # 1996-01-01


def fetch_ticker(ticker: str) -> tuple[int, str]:
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
    adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
    for i in range(len(ts)):
        def val(arr):
            if i < len(arr) and arr[i] is not None:
                return f"{arr[i]:.4f}"
            return ""
        d = time.strftime("%m/%d/%Y", time.gmtime(ts[i]))
        lines.append(
            f"{d},{val(quote.get('open', []))},{val(quote.get('high', []))},"
            f"{val(quote.get('low', []))},{val(quote.get('close', []))},"
            f"{val(quote.get('volume', []))},{val(adj)}"
        )
    return len(ts), "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for ticker in ORIGINAL19:
        try:
            n, text = fetch_ticker(ticker)
            path = OUT_DIR / f"{ticker}_historical.csv"
            path.write_text(text + "\n", encoding="utf-8")
            print(f"{ticker}: {n} rows -> {path.name}", flush=True)
            time.sleep(0.2)
        except Exception as e:
            failures.append((ticker, str(e)))
            print(f"{ticker}: FAIL {e}", flush=True)
    if failures:
        print("failures:", failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
