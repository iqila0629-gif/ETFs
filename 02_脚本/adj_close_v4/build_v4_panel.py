"""Build v4 panels limited to original 19 ETFs plus external data."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import config


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    fund = pd.read_csv(config.FUND_PANEL)
    if "date" in fund.columns:
        fund = fund.rename(columns={"date": "Date"})
    etf = pd.read_csv(config.ETF19_PANEL)
    external = pd.read_csv(config.EXTERNAL_DAILY, parse_dates=["Date"])

    fund["Date"] = pd.to_datetime(fund["Date"])
    etf["Date"] = pd.to_datetime(etf["Date"])

    fund_cols = list(fund.columns[1:])
    etf_cols = list(etf.columns[1:])
    fund_outliers = int((fund[fund_cols].abs() > config.FUND_RETURN_CLIP).sum().sum())
    etf_outliers = int((etf[etf_cols].abs() > config.ETF_RETURN_CLIP).sum().sum())
    fund[fund_cols] = fund[fund_cols].clip(
        -config.FUND_RETURN_CLIP, config.FUND_RETURN_CLIP
    )
    etf[etf_cols] = etf[etf_cols].clip(
        -config.ETF_RETURN_CLIP, config.ETF_RETURN_CLIP
    )

    panel = (
        fund.merge(etf, on="Date", how="left")
        .sort_values("Date")
        .reset_index(drop=True)
    )

    keep_ext = ["Date"] + [
        c
        for c in external.columns
        if c.startswith(("VIX", "TNX", "Credit", "JNK", "USD", "Sect", "Yld", "Stk"))
    ]
    external = external[keep_ext].sort_values("Date").reset_index(drop=True)

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.to_csv(config.V4_ETF19_PANEL, index=False)
    external.to_csv(config.V4_EXTERNAL_PANEL, index=False)

    fund_cols = set(fund.columns[1:])
    etf_cols = [c for c in panel.columns if c not in fund_cols and c != "Date"]
    outside = [c for c in etf_cols if c not in config.ORIGINAL19]
    print(f"v4 panel rows: {len(panel)}, range {panel['Date'].iloc[0].date()} .. {panel['Date'].iloc[-1].date()}")
    print(f"etf cols: {len(etf_cols)} -> {sorted(etf_cols)}")
    print(f"clipped fund outliers: {fund_outliers}, ETF outliers: {etf_outliers}")
    print(f"outside original19: {outside}")
    print(f"saved: {config.V4_ETF19_PANEL}")
    print(f"saved: {config.V4_EXTERNAL_PANEL}")


if __name__ == "__main__":
    main()
