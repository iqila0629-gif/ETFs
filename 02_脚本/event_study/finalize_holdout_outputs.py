"""Generate frozen-holdout (2025-2026) final CSVs and rebuild the daily union."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_daily_tables import write_daily_wide
from generate_predictions import write_standard_csv


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
DAILY_OUT = OUT_DIR / "daily_sparse_predictions_all_funds.csv"
SUMMARY_OUT = OUT_DIR / "sparse_funds_summary.csv"
CUTOFF = pd.Timestamp("2025-01-01")

ONE_DAY_FOLDERS = [
    ("sparse_outputs_full_history", "sparse_outputs"),
    ("sparse_outputs_self_full_history", "sparse_outputs_self"),
    ("sparse_outputs_external_full_history", "sparse_outputs_external"),
    ("sparse_outputs_extended_full_history", "sparse_outputs_extended"),
    ("sparse_outputs_blank_funds_full_history", "sparse_outputs_blank_funds"),
]
MULTI_DAY_FOLDERS = [
    ("sparse_outputs_multi_day_full_history", "sparse_outputs_multi_day"),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    total_files = 0
    verified = 0
    failed: list[str] = []
    by_fund: dict[str, dict[pd.Timestamp, float]] = {}

    for src_name, dst_name in ONE_DAY_FOLDERS + MULTI_DAY_FOLDERS:
        src = OUT_DIR / src_name
        dst = OUT_DIR / dst_name
        dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(src.glob("*.csv")):
            df = pd.read_csv(path, skiprows=12)
            df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
            col = df.columns[1]
            sub = df[df["Date"] >= CUTOFF].copy()
            if sub.empty:
                failed.append(f"{dst_name}/{path.name}: no holdout trades")
                continue
            rows = [
                (date.strftime("%m/%d/%Y"), value)
                for date, value in zip(sub["Date"], sub[col])
            ]
            out_path = dst / path.name
            write_standard_csv(out_path, rows)
            total_files += 1
            avg = float(sub[col].mean())
            if avg >= 0.2 or avg <= -0.2:
                verified += 1
            else:
                failed.append(f"{dst_name}/{path.name}: average {avg:.4f}")
            if dst_name in ("sparse_outputs", "sparse_outputs_self", "sparse_outputs_external", "sparse_outputs_extended", "sparse_outputs_blank_funds"):
                ticker = path.stem.split("__", 1)[0]
                by_fund.setdefault(ticker, {}).update(
                    dict(zip(sub["Date"], sub[col]))
                )

    fund = wf.load_panel(wf.FUND_PANEL)
    all_tickers = list(fund.columns[1:])
    dates_desc = fund["Date"].sort_values(ascending=False).tolist()
    by_fund_full = {ticker: by_fund.get(ticker, {}) for ticker in all_tickers}
    write_daily_wide(DAILY_OUT, dates_desc, all_tickers, by_fund_full)

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
    summary.to_csv(SUMMARY_OUT, index=False)

    print(f"Final CSVs generated: {total_files}")
    print(f"Average check passed: {verified}")
    print(f"Problems: {len(failed)}")
    for message in failed[:30]:
        print(f"  {message}")
    print(f"Holdout funds with 1-day signals: {len(by_fund)}")
    print(f"Daily union trigger cells: {sum(len(v) for v in by_fund_full.values())}")
    print(f"Saved: {DAILY_OUT}")
    print(f"Saved: {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
