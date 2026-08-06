"""Build adjusted-close (total return) tables for funds and ETFs."""

from __future__ import annotations

import csv
import json
import pathlib
import sys

import pandas as pd


ROOT = pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测")
FUND_JSON = ROOT / "raw_data" / "profunds" / "adj_close_nasdaq"
ETF19_DIR = ROOT / "raw_data" / "etfs"
ETF57_DIR = ROOT / "raw_data" / "etfs_extended_full"
OUT = ROOT / "processed_returns"
EVENT = ROOT / "analysis_results" / "event_study"


def write_13line(path: pathlib.Path, df: pd.DataFrame) -> None:
    """Write company 13-line CSV from a Date-first wide table (dates desc)."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([])
        for stat in ["Hit Ratio", "Up Count", "Down Count", "Average", "Max", "Min", "Count", "Std", "Sum"]:
            row = [stat]
            for col in df.columns[1:]:
                vals = df[col].dropna()
                if vals.empty:
                    row.append("")
                    continue
                up = int((vals > 0).sum())
                down = int((vals < 0).sum())
                if stat == "Hit Ratio":
                    row.append(f"{up/(up+down):.6f}" if up + down else "")
                elif stat == "Up Count":
                    row.append(str(up))
                elif stat == "Down Count":
                    row.append(str(down))
                elif stat == "Average":
                    row.append(f"{vals.mean():.6f}")
                elif stat == "Max":
                    row.append(f"{vals.max():.6f}")
                elif stat == "Min":
                    row.append(f"{vals.min():.6f}")
                elif stat == "Count":
                    row.append(str(int(vals.count())))
                elif stat == "Std":
                    row.append(f"{vals.std(ddof=1):.6f}" if len(vals) > 1 else "")
                elif stat == "Sum":
                    row.append(f"{vals.sum():.6f}")
            writer.writerow(row)
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Date", *df.columns[1:]])
        for _, row in df.iterrows():
            date_str = row["Date"].strftime("%m/%d/%Y")
            writer.writerow([date_str, *("" if pd.isna(row[c]) else f"{row[c]:.6f}" for c in df.columns[1:])])


def load_fund_adj() -> pd.DataFrame:
    frames = []
    for p in sorted(FUND_JSON.glob("*.json")):
        ticker = p.stem
        with p.open(encoding="utf-8-sig") as fh:
            payload = json.load(fh)
        rows = payload["data"]["tradesTable"]["rows"]
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
        df[ticker] = pd.to_numeric(df["adjustedClose"].astype(str).str.replace(",", ""), errors="coerce")
        frames.append(df[["date", ticker]])
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)
    return merged


def load_etf_adj(dir_path: pathlib.Path) -> pd.DataFrame:
    frames = []
    for p in sorted(dir_path.glob("*.csv")):
        ticker = p.name.replace("_historical.csv", "").replace(".csv", "")
        df = pd.read_csv(p)
        df.columns = [c.strip() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        df = df[["Date", "Adj Close"]].rename(columns={"Adj Close": ticker})
        frames.append(df)
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="Date", how="outer")
    merged = merged.sort_values("Date").reset_index(drop=True)
    return merged


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    EVENT.mkdir(parents=True, exist_ok=True)

    # 1. Fund adjusted NAV + daily returns panel
    fund_adj = load_fund_adj()
    fund_adj_desc = fund_adj.sort_values("date", ascending=False).reset_index(drop=True)
    fund_adj_desc = fund_adj_desc.rename(columns={"date": "Date"})
    fund_adj_desc["Date"] = fund_adj_desc["Date"].dt.strftime("%m/%d/%Y")
    fund_adj_desc.to_csv(OUT / "combined_profunds_adj_nav.csv", index=False)

    fund_ret = fund_adj.copy()
    for col in fund_adj.columns[1:]:
        fund_ret[col] = fund_adj[col].pct_change(fill_method=None)
    fund_ret.to_csv(EVENT / "panel_fund_returns_adj.csv", index=False)

    fund_ret_desc = fund_ret.sort_values("date", ascending=False).reset_index(drop=True)
    fund_ret_desc = fund_ret_desc.rename(columns={"date": "Date"})
    for col in fund_ret_desc.columns[1:]:
        fund_ret_desc[col] = fund_ret_desc[col] * 100
    write_13line(OUT / "combined_profunds_adj_returns.csv", fund_ret_desc)

    # 2. ETF adjusted returns (19 and 57)
    etf19 = load_etf_adj(ETF19_DIR)
    etf19_ret = etf19.copy()
    for col in etf19.columns[1:]:
        etf19_ret[col] = etf19[col].pct_change(fill_method=None) * 100
    etf19_ret_desc = etf19_ret.sort_values("Date", ascending=False).reset_index(drop=True)
    write_13line(OUT / "combined_etf_returns_adj.csv", etf19_ret_desc)
    etf19_ret.to_csv(EVENT / "panel_etf_returns_adj.csv", index=False)

    etf57 = load_etf_adj(ETF57_DIR)
    etf57_ret = etf57.copy()
    for col in etf57.columns[1:]:
        etf57_ret[col] = etf57[col].pct_change(fill_method=None) * 100
    etf57_ret_desc = etf57_ret.sort_values("Date", ascending=False).reset_index(drop=True)
    write_13line(OUT / "combined_extended_etf_returns_adj.csv", etf57_ret_desc)

    print("fund adj NAV rows:", len(fund_adj))
    print("fund adj start:", fund_adj["date"].min().date(), "end:", fund_adj["date"].max().date())
    print("etf19 rows:", len(etf19), "etf57 rows:", len(etf57))
    print("saved to:", OUT)


if __name__ == "__main__":
    main()
