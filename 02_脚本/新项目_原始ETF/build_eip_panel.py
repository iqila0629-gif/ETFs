# -*- coding: utf-8 -*-
"""Build EIP analysis panel: Date + fund Adj Close returns (decimal) + original-19 ETF returns (percent).

Base calendar = ETF trading dates from panel_etf_returns_adj.csv; fund returns are
merged left (NaN where a fund did not trade). Funds with <120 actual rows after
download are routed to 01_数据/eip_data_insufficient.csv and excluded from the panel.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config_eip as config


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.MIDDLE.mkdir(parents=True, exist_ok=True)

    targets = config.load_clean_targets()
    etf = pd.read_csv(config.ETF_PANEL)
    etf["Date"] = pd.to_datetime(etf["Date"]).dt.strftime("%Y-%m-%d")
    etf = etf.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)
    missing_etf = [c for c in config.ORIGINAL19 if c not in etf.columns]
    if missing_etf:
        print("missing ETF cols:", missing_etf)
        sys.exit(1)

    panel = etf.copy()
    insufficient: list[dict] = []
    n_ok = 0
    for _, t in targets.iterrows():
        name = t["name"]
        safe = "".join(ch for ch in name if ch not in '\\/:*?"<>|')
        path = config.CLEANED_DIR / f"{safe}.csv"
        if not path.exists():
            insufficient.append({"name": name, "category": t["category"], "symbol": t["symbol"], "rows": 0, "reason": "下载缺失"})
            print(f"[skip] no file: {name}", flush=True)
            continue
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df = df.dropna(subset=["Adj Close"]).drop_duplicates("Date", keep="last")
        if len(df) < config.RECOMMENDED_FULL_TRADES:
            insufficient.append({"name": name, "category": t["category"], "symbol": t["symbol"], "rows": len(df), "reason": "实测行数不足120"})
            print(f"[skip] insufficient rows: {name} ({len(df)})", flush=True)
            continue
        df = df.sort_values("Date").reset_index(drop=True)
        ret = df["Adj Close"].pct_change().clip(-config.FUND_RETURN_CLIP, config.FUND_RETURN_CLIP)
        s = pd.DataFrame({"Date": df["Date"], name: ret})
        panel = panel.merge(s, on="Date", how="left")
        n_ok += 1

    panel = panel.sort_values("Date").reset_index(drop=True)
    fund_cols = [c for c in panel.columns if c not in {"Date"} | set(config.ORIGINAL19)]
    etf_cols = config.ORIGINAL19

    # validation
    print("panel rows:", len(panel), "range:", panel["Date"].iloc[0], "..", panel["Date"].iloc[-1])
    print("fund cols:", len(fund_cols))
    print("etf cols in panel:", len([c for c in etf_cols if c in panel.columns]), "/", len(etf_cols))
    nonfinite_funds = int(panel[fund_cols].isna().sum().sum()) if fund_cols else 0
    print("fund NaN cells:", nonfinite_funds)

    panel.to_csv(config.PANEL_PATH, index=False, encoding="utf-8-sig")
    if insufficient:
        pd.DataFrame(insufficient).to_csv(config.DATA_INSUFFICIENT, index=False, encoding="utf-8-sig")
        print("data-insufficient funds:", len(insufficient), "->", config.DATA_INSUFFICIENT)
    else:
        print("no data-insufficient funds")
    print("saved panel:", config.PANEL_PATH)


if __name__ == "__main__":
    main()