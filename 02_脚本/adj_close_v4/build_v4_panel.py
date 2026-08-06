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
    external = pd.read_csv(config.EXTERNAL_DAILY, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)

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

    vix = external["VIX_Close"]
    tnx = external["TNX_Yield"]
    ext = pd.DataFrame({"Date": external["Date"]})
    etf_for_ext = etf[
        ["Date", "SPY", "HYG", "TLT", "JNK", "UUP", "GLD", "XLK", "XLF", "TIP"]
    ].sort_values("Date")
    ext = ext.merge(etf_for_ext, on="Date", how="left")
    ext["VIX_Close"] = vix.to_numpy()
    ext["VIX_Chg%"] = vix.pct_change() * 100
    ext["TNX_Yield"] = tnx.to_numpy()
    ext["TNX_ChgBp"] = tnx.diff() * 100
    ext["CreditSpread"] = ext["HYG"] - ext["TLT"]
    ext["JNKSpread"] = ext["JNK"] - ext["TLT"]
    ext["StkBonCorr"] = ext["SPY"].rolling(20).corr(ext["TLT"])
    ext["USDGoldRatio"] = ext["UUP"] - ext["GLD"]
    ext["SectRotation"] = ext["XLK"] - ext["XLF"]
    ext["VIX_5dChg"] = vix.pct_change(5) * 100
    ext["VIX_20dVol"] = vix.pct_change().rolling(20).std() * 100
    ext["VIX_TNX_Ratio"] = vix / tnx
    ext["YldCurveProxy"] = ext["TLT"] - ext["TIP"]
    ext = ext.drop(columns=["SPY", "HYG", "TLT", "JNK", "UUP", "GLD", "XLK", "XLF", "TIP"])
    external = ext.sort_values("Date").reset_index(drop=True)

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.to_csv(config.V4_ETF19_PANEL, index=False)
    external.to_csv(config.V4_EXTERNAL_PANEL, index=False)

    xlc_raw = pd.read_csv(config.BACKUP_EXT_DIR / "XLC.csv")
    xlc_raw["Date"] = pd.to_datetime(xlc_raw["Date"])
    xlc_raw = xlc_raw.sort_values("Date").reset_index(drop=True)
    xlc_ret = xlc_raw["Adj Close"].pct_change() * 100
    xlc_ret = xlc_ret.clip(-config.ETF_RETURN_CLIP, config.ETF_RETURN_CLIP)
    xlc_panel = pd.DataFrame({"Date": xlc_raw["Date"], "XLC": xlc_ret})
    panel20 = panel.merge(xlc_panel, on="Date", how="left")
    panel20.to_csv(config.V4_ETF20_PANEL, index=False)

    fund_cols = set(fund.columns[1:])
    etf_cols = [c for c in panel.columns if c not in fund_cols and c != "Date"]
    etf_cols20 = [c for c in panel20.columns if c not in fund_cols and c != "Date"]
    outside = [c for c in etf_cols20 if c not in config.V4_UNIVERSE]
    print(f"v4 panel rows: {len(panel)}, range {panel['Date'].iloc[0].date()} .. {panel['Date'].iloc[-1].date()}")
    print(f"etf cols: {len(etf_cols)} -> {sorted(etf_cols)}")
    print(f"v4_etf20 cols: {len(etf_cols20)} -> {sorted(etf_cols20)}")
    print(f"clipped fund outliers: {fund_outliers}, ETF outliers: {etf_outliers}")
    print("note: VIX_Chg%/TNX_ChgBp and derived external columns recomputed from raw levels")
    print(f"outside original19: {outside}")
    print(f"saved: {config.V4_ETF19_PANEL}")
    print(f"saved: {config.V4_ETF20_PANEL}")
    print(f"saved: {config.V4_EXTERNAL_PANEL}")


if __name__ == "__main__":
    main()
