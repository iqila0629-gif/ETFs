"""Clean anomalous adjustedClose jumps in ProFunds JSON history."""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

import config


THRESHOLD = 0.5  # daily return >= 50% is treated as anomaly
SOURCE_DIR = config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始" / "profunds" / "adj_close_nasdaq"
OUT_DIR = config.PROCESSED / "profunds_adj_cleaned"
LOG_PATH = config.PROCESSED / "profunds_cleaning_log.csv"


def load_series(path: pathlib.Path) -> tuple[list[pd.Timestamp], np.ndarray, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data["data"]["tradesTable"]["rows"]
    dates = []
    closes = []
    for r in rows:
        dates.append(pd.to_datetime(r["date"], format="%m/%d/%Y"))
        closes.append(float(r["adjustedClose"]))
    order = np.argsort(dates)
    dates_sorted = [dates[i] for i in order]
    closes_sorted = np.array([closes[i] for i in order], dtype=float)
    return dates_sorted, closes_sorted, data


def fix_series(closes: np.ndarray, dates: list[pd.Timestamp], ticker: str) -> tuple[np.ndarray, list[dict]]:
    closes = closes.copy()
    log: list[dict] = []
    while True:
        returns = np.divide(closes[1:], closes[:-1], out=np.zeros_like(closes[:-1]), where=closes[:-1] != 0) - 1
        bad = np.where(np.abs(returns) >= THRESHOLD)[0]
        if len(bad) == 0:
            break
        i = int(bad[0])  # anomaly at date index i+1
        pre = closes[i]
        spike = closes[i + 1]
        j = i + 2
        while j < len(closes) and abs(closes[j] / spike - 1) < 0.05:
            j += 1
        if j >= len(closes):
            kind = "level_shift"
            factor = spike / pre if pre != 0 else 1.0
            closes[: i + 1] = closes[: i + 1] * factor
            log.append({
                "fund": ticker,
                "date": dates[i + 1].strftime("%Y-%m-%d"),
                "old_close": float(spike),
                "new_close": float(closes[i + 1]),
                "type": kind,
                "factor": float(factor),
            })
            continue
        ratio = closes[j] / pre if pre != 0 else 0.0
        if 0.5 <= ratio <= 1.5:
            kind = "spike"
            for k in range(i + 1, j):
                log.append({
                    "fund": ticker,
                    "date": dates[k].strftime("%Y-%m-%d"),
                    "old_close": float(closes[k]),
                    "new_close": float(pre),
                    "type": kind,
                    "factor": 1.0,
                })
            closes[i + 1 : j] = pre
        else:
            kind = "level_shift"
            factor = spike / pre if pre != 0 else 1.0
            closes[: i + 1] = closes[: i + 1] * factor
            log.append({
                "fund": ticker,
                "date": dates[i + 1].strftime("%Y-%m-%d"),
                "old_close": float(spike),
                "new_close": float(closes[i + 1]),
                "type": kind,
                "factor": float(factor),
            })
    return closes, log


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_log: list[dict] = []
    files = sorted(SOURCE_DIR.glob("*.json"))
    for path in files:
        ticker = path.stem
        dates, closes, data = load_series(path)
        cleaned, log = fix_series(closes, dates, ticker)
        all_log.extend(log)
        rows = data["data"]["tradesTable"]["rows"]
        close_by_date = {d: float(v) for d, v in zip(dates, cleaned)}
        for r in rows:
            d = pd.to_datetime(r["date"], format="%m/%d/%Y")
            r["adjustedClose"] = close_by_date[d]
        out_path = OUT_DIR / f"{ticker}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if log:
            print(f"{ticker}: {len(log)} fixes")
    pd.DataFrame(all_log).to_csv(LOG_PATH, index=False)
    print(f"total fixes: {len(all_log)}")
    print("saved:", LOG_PATH)
    print("saved cleaned dir:", OUT_DIR)


if __name__ == "__main__":
    main()
