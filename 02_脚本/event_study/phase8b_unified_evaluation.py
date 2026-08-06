"""Unified evaluation: compare new ETF signals vs existing signals on 2025-2026."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import event_metrics as em


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
MAIN_PREDICTIONS = OUT_DIR / "predictions"
SPARSE_FOLDERS = [
    OUT_DIR / "sparse_outputs",
    OUT_DIR / "sparse_outputs_self",
    OUT_DIR / "sparse_outputs_external",
    OUT_DIR / "sparse_outputs_multi_day",
    OUT_DIR / "sparse_outputs_extended",
    OUT_DIR / "sparse_outputs_blank_funds",
]
SCAN = OUT_DIR / "optimization_scan.csv"
SUMMARY = OUT_DIR / "optimization_summary_unified.csv"
CUTOFF = pd.Timestamp("2025-01-01")


def file_holdout_avg(path: pathlib.Path, already_holdout: bool = False) -> float:
    df = pd.read_csv(path, skiprows=12)
    col = df.columns[1]
    if not already_holdout:
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        df = df[df["Date"] >= CUTOFF]
    if df.empty:
        return float("nan")
    return float(df[col].mean())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    existing: dict[str, dict] = {}

    def update(ticker: str, avg: float, condition: str, source: str) -> None:
        if avg != avg:
            return
        if ticker not in existing or abs(avg) > abs(existing[ticker]["avg"]):
            existing[ticker] = {"avg": avg, "condition": condition, "source": source}

    for path in sorted(MAIN_PREDICTIONS.glob("*.csv")):
        ticker = path.stem.split("__", 1)[0]
        condition = path.stem.split("__", 1)[1] if "__" in path.stem else ""
        update(ticker, file_holdout_avg(path), condition, "main")

    for folder in SPARSE_FOLDERS:
        if not folder.exists():
            continue
        for path in folder.glob("*.csv"):
            ticker = path.stem.split("__", 1)[0]
            condition = path.stem.split("__", 1)[1] if "__" in path.stem else ""
            update(ticker, file_holdout_avg(path, already_holdout=True), condition, folder.name)

    scan = pd.read_csv(SCAN)
    summary_rows = []
    for ticker, group in scan.groupby("ticker"):
        row = group.reindex(group["holdout_avg"].abs().sort_values(ascending=False).index).iloc[0]
        old = existing.get(ticker)
        old_avg = old["avg"] if old else float("nan")
        improved = (old is None) or abs(row["holdout_avg"]) > abs(old_avg)
        summary_rows.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "existing_holdout_avg": round(old_avg, 4) if old else "",
                "existing_condition": old["condition"] if old else "",
                "existing_source": old["source"] if old else "",
                "new_best_condition": row["condition"],
                "new_horizon": row["horizon"],
                "new_holdout_trades": row["holdout_trades"],
                "new_holdout_hit_rate": row["holdout_hit_rate"],
                "new_holdout_avg": row["holdout_avg"],
                "improved": improved,
            }
        )
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary = summary.sort_values("new_holdout_avg", key=lambda s: s.abs(), ascending=False)
    summary.to_csv(SUMMARY, index=False)

    improved = summary[summary["improved"]] if not summary.empty else summary
    strict = scan[(scan["holdout_trades"] >= 20) & (scan["holdout_hit_rate"] >= 0.6)]
    strict_funds = set(strict["ticker"])
    strict_improved = improved[improved["ticker"].isin(strict_funds)] if not improved.empty else improved

    print(f"Existing funds with 2025-2026 holdout average: {len(existing)}")
    print(f"New-signal funds: {summary['ticker'].nunique() if not summary.empty else 0}")
    print(f"Unified improved (new > existing holdout): {len(improved)}")
    print(f"Strict subset funds: {len(strict_funds)}")
    print(f"Strict improved: {strict_improved['ticker'].nunique() if not strict_improved.empty else 0}")
    if not improved.empty:
        cols = ["ticker", "existing_holdout_avg", "existing_condition", "existing_source", "new_best_condition", "new_horizon", "new_holdout_trades", "new_holdout_hit_rate", "new_holdout_avg"]
        print(improved[cols].head(20).to_string(index=False))
    print(f"Saved: {SUMMARY}")


if __name__ == "__main__":
    main()
