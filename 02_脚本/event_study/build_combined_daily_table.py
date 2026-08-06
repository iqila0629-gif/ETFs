"""Merge main-model daily signals with sparse-study 1-day signals."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_daily_tables import write_daily_wide


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
MAIN_DAILY = OUT_DIR / "daily_predictions_all_funds.csv"
COMBINED = OUT_DIR / "daily_predictions_all_funds_combined.csv"
SUMMARY = OUT_DIR / "daily_combined_funds_summary.csv"
SPARSE_FOLDERS = [
    OUT_DIR / "sparse_outputs_full_history",
    OUT_DIR / "sparse_outputs_self_full_history",
    OUT_DIR / "sparse_outputs_external_full_history",
    OUT_DIR / "sparse_outputs_extended_full_history",
    OUT_DIR / "sparse_outputs_blank_funds_full_history",
]


def load_daily(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=12)
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    return df


def series_by_fund(df: pd.DataFrame) -> dict[str, dict[pd.Timestamp, float]]:
    out: dict[str, dict[pd.Timestamp, float]] = {}
    for col in df.columns[1:]:
        sub = df[["Date", col]].dropna()
        if not sub.empty:
            out[col] = dict(zip(sub["Date"], sub[col]))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main_df = load_daily(MAIN_DAILY)
    main_by_fund = series_by_fund(main_df)
    main_tickers = set(main_by_fund)

    sparse_by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    for folder in SPARSE_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.glob("*.csv"):
            ticker = path.stem.split("__", 1)[0]
            sub = load_daily(path)[["Date", "Daily Return (%)"]].dropna()
            if not sub.empty:
                sparse_by_fund.setdefault(ticker, {}).update(
                    dict(zip(sub["Date"], sub["Daily Return (%)"]))
                )

    by_fund = dict(main_by_fund)
    for ticker, values in sparse_by_fund.items():
        if ticker not in main_tickers:
            by_fund.setdefault(ticker, {}).update(values)

    fund = wf.load_panel(wf.FUND_PANEL)
    all_tickers = list(fund.columns[1:])
    dates_desc = fund["Date"].sort_values(ascending=False).tolist()
    by_fund_full = {ticker: by_fund.get(ticker, {}) for ticker in all_tickers}
    write_daily_wide(COMBINED, dates_desc, all_tickers, by_fund_full)

    summary_rows = []
    for ticker in all_tickers:
        values = pd.Series(list(by_fund_full[ticker].values()), dtype="float64")
        if values.empty:
            continue
        up = int((values > 0).sum())
        summary_rows.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "trigger_days": int(len(values)),
                "hit_rate": round(up / len(values), 4),
                "average": round(float(values.mean()), 4),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("ticker")
    summary.to_csv(SUMMARY, index=False)

    covered_1d = set(by_fund)
    multi = pd.read_csv(OUT_DIR / "multi_day_validation.csv", keep_default_na=False)
    multi_funds = set(multi.loc[multi["pass_and_reliable"], "ticker"])
    multi_only = sorted(multi_funds - covered_1d)
    remaining = sorted(set(all_tickers) - covered_1d - set(multi_only))

    print(f"Fund columns with values (main + sparse 1-day): {len(covered_1d)} / {len(all_tickers)}")
    print(f"Multi-day-only funds (kept separate): {len(multi_only)} {multi_only}")
    print(f"Total covered incl multi-day: {len(covered_1d | set(multi_only))} / {len(all_tickers)}")
    print(f"Remaining blank funds: {len(remaining)} {remaining}")
    print(f"Trigger cells in combined table: {sum(len(v) for v in by_fund_full.values())}")
    print(f"Saved: {COMBINED}")
    print(f"Saved: {SUMMARY}")


if __name__ == "__main__":
    main()
