"""Process Nasdaq-downloaded extended ETF data into standard tables."""

from __future__ import annotations

import csv
import json
import pathlib
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_daily_tables import write_daily_wide


ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "raw_data" / "etfs_extended"
ETF_OUT_DIR = ROOT / "processed_returns" / "extended_etf_returns"
COMBINED = ROOT / "processed_returns" / "combined_extended_etf_returns.csv"
EVENT_DIR = ROOT / "analysis_results" / "event_study"
CORR_OUT = EVENT_DIR / "extended_etf_correlation.csv"
BEST_OUT = EVENT_DIR / "extended_etf_best_conditions.csv"
FUND_PANEL = EVENT_DIR / "panel_fund_returns.csv"

REMAINING_FUNDS = [
    "GVPIX",
    "RDPIX",
    "RDPSX",
    "RRPIX",
    "RRPSX",
    "RTPIX",
    "RTPSX",
]

def load_nasdaq(path: pathlib.Path) -> pd.DataFrame:
    with path.open(encoding="utf-8-sig") as fh:
        payload = json.load(fh)
    rows = payload["data"]["tradesTable"]["rows"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
    df["close"] = pd.to_numeric(df["close"].astype(str).str.replace(",", ""), errors="coerce")
    df = df[["date", "close"]].dropna().sort_values("date").reset_index(drop=True)
    return df


def write_standard_csv(path: pathlib.Path, rows: list[tuple[str, float]]) -> None:
    values = pd.Series([value for _, value in rows])
    count = int(values.count())
    up = int((values > 0).sum())
    down = int((values < 0).sum())
    hit = up / (up + down) if (up + down) else float("nan")
    std = float(values.std(ddof=1)) if count > 1 else float("nan")

    def fmt(value: float) -> str:
        return "" if value != value else f"{value:.6f}"

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([])
        writer.writerow(["Hit Ratio", fmt(hit)])
        writer.writerow(["Up Count", up])
        writer.writerow(["Down Count", down])
        writer.writerow(["Average", fmt(float(values.mean()))])
        writer.writerow(["Max", fmt(float(values.max()))])
        writer.writerow(["Min", fmt(float(values.min()))])
        writer.writerow(["Count", count])
        writer.writerow(["Std", fmt(std)])
        writer.writerow(["Sum", fmt(float(values.sum()))])
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Date", "Daily Return (%)"])
        for date_str, value in rows:
            writer.writerow([date_str, f"{value:.6f}"])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ETF_OUT_DIR.mkdir(parents=True, exist_ok=True)
    etf_by_ticker: dict[str, pd.DataFrame] = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        ticker = path.stem.upper()
        if ticker == "QQQ_NASDAQ":
            continue
        etf_by_ticker[ticker] = load_nasdaq(path)

    tickers = sorted(etf_by_ticker)
    etf_panel = pd.DataFrame({"Date": etf_by_ticker[tickers[0]]["date"]})
    for ticker in tickers:
        df = etf_by_ticker[ticker]
        etf_panel = etf_panel.merge(df.rename(columns={"date": "Date"}), on="Date", how="outer")
        etf_panel = etf_panel.rename(columns={"close": ticker})
    etf_panel = etf_panel.sort_values("Date").reset_index(drop=True)
    for ticker in tickers:
        etf_panel[ticker] = etf_panel[ticker].pct_change(fill_method=None) * 100

    by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    for ticker in tickers:
        sub = etf_panel[["Date", ticker]].dropna()
        rows = [
            (date.strftime("%m/%d/%Y"), value)
            for date, value in zip(sub["Date"], sub[ticker])
        ]
        path = ETF_OUT_DIR / f"{ticker}.csv"
        write_standard_csv(path, rows)
        by_fund[ticker] = dict(zip(sub["Date"], sub[ticker]))

    dates_desc = etf_panel["Date"].sort_values(ascending=False).tolist()
    write_daily_wide(COMBINED, dates_desc, tickers, by_fund)

    fund = wf.load_panel(FUND_PANEL)
    merged = fund.merge(etf_panel, on="Date", how="inner")
    corr_rows = []
    for ticker in tickers:
        etf_ret = merged[ticker]
        for fund_col in fund.columns[1:]:
            fund_ret = merged[fund_col]
            valid = merged[etf_ret.notna() & fund_ret.notna()]
            if len(valid) < 60:
                continue
            same = float(valid[ticker].corr(valid[fund_col]))
            tomorrow = valid[fund_col].shift(-1)
            both = pd.concat([valid[ticker], tomorrow], axis=1).dropna()
            lead1 = float(both.iloc[:, 0].corr(both.iloc[:, 1])) if len(both) > 60 else float("nan")
            agree = float((((both.iloc[:, 0] > 0) & (both.iloc[:, 1] > 0)) | ((both.iloc[:, 0] < 0) & (both.iloc[:, 1] < 0))).mean()) if len(both) > 60 else float("nan")
            corr_rows.append(
                {
                    "ETF": ticker,
                    "Fund": fund_col,
                    "N": len(valid),
                    "Same": round(same, 4),
                    "Lead1": round(lead1, 4) if lead1 == lead1 else "",
                    "DirAgree": round(agree, 4) if agree == agree else "",
                }
            )
    corr = pd.DataFrame(corr_rows)
    corr.to_csv(CORR_OUT, index=False)

    best_rows = []
    for fund_col in REMAINING_FUNDS:
        tomorrow = merged[fund_col].shift(-1)
        for ticker in tickers:
            s = merged[ticker]
            conditions = [
                (f"{ticker}_up", s > 0),
                (f"{ticker}_down", s < 0),
                (f"{ticker}_big_up", s >= 1.0),
                (f"{ticker}_big_down", s <= -1.0),
                (f"{ticker}_gt2", s > 2.0),
                (f"{ticker}_lt-2", s < -2.0),
            ]
            for name, mask in conditions:
                metrics = em.condition_metrics(mask, tomorrow)
                if metrics["n"] < 100:
                    continue
                p = max(metrics["p_up"], metrics["p_down"])
                if p >= 0.52 and abs(metrics["expected"]) >= 0.15:
                    best_rows.append(
                        {
                            "ticker": fund_col,
                            "condition": name,
                            **metrics,
                        }
                    )
    best = pd.DataFrame(best_rows)
    if not best.empty:
        best = best.sort_values("expected", key=lambda s: s.abs(), ascending=False)
    best.to_csv(BEST_OUT, index=False)

    print(f"ETFs processed: {len(tickers)}")
    print(f"Date range: {etf_panel['Date'].iloc[0].date()} .. {etf_panel['Date'].iloc[-1].date()}")
    print(f"Saved per-ETF CSVs to: {ETF_OUT_DIR}")
    print(f"Saved combined: {COMBINED}")
    print(f"Correlation rows: {len(corr)}")
    print(f"Best-condition rows for remaining funds: {len(best)}")
    if not best.empty:
        print(best.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
