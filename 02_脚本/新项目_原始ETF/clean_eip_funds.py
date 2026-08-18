# -*- coding: utf-8 -*-
"""Clean EIP fund Adj Close series (reuse v4 clean_profunds_outliers logic).

Single-day spikes (>=50% daily move) are back-filled to the previous close;
level shifts (split/rebasing artifacts) adjust the earlier part of the series.
Outputs cleaned CSVs to 01_数据/新项目_processed/eip_cleaned/ and a cleaning log.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import config_eip as config


THRESHOLD = 0.5  # daily return >= 50% treated as anomaly


def fix_series(closes: np.ndarray, dates: list[str], fund: str) -> tuple[np.ndarray, list[dict]]:
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
                "fund": fund,
                "date": dates[i + 1],
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
                    "fund": fund,
                    "date": dates[k],
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
                "fund": fund,
                "date": dates[i + 1],
                "old_close": float(spike),
                "new_close": float(closes[i + 1]),
                "type": kind,
                "factor": float(factor),
            })
    return closes, log


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    all_log: list[dict] = []
    files = sorted(config.PRICE_DIR.glob("*.csv"))
    for path in files:
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.dropna(subset=["Adj Close"]).sort_values("Date")
        df = df.drop_duplicates("Date", keep="last")
        dates = [d.strftime("%Y-%m-%d") for d in df["Date"]]
        closes = df["Adj Close"].to_numpy(dtype=float)
        cleaned, log = fix_series(closes, dates, path.stem)
        all_log.extend(log)
        out = df.copy()
        out["Adj Close"] = cleaned
        out.to_csv(config.CLEANED_DIR / path.name, index=False, encoding="utf-8-sig")
        if log:
            print(f"{path.stem}: {len(log)} fixes")
    if all_log:
        pd.DataFrame(all_log).to_csv(config.CLEANING_LOG, index=False, encoding="utf-8-sig")
    print(f"cleaned files: {len(files)}  total fixes: {len(all_log)}")
    print(f"saved dir: {config.CLEANED_DIR}")
    if all_log:
        print(f"saved log: {config.CLEANING_LOG}")


if __name__ == "__main__":
    main()