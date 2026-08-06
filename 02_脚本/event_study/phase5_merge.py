"""Phase 5: merge all validated sparse signals and build the daily union table."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_daily_tables import write_daily_wide


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
ALL_VALIDATED = OUT_DIR / "sparse_all_validated.csv"
DAILY_OUT = OUT_DIR / "daily_sparse_predictions_all_funds.csv"
SUMMARY_OUT = OUT_DIR / "sparse_funds_summary.csv"


def load_validated(path: pathlib.Path, source: str, pass_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, keep_default_na=False)
    df = df[df[pass_col].astype(str).isin(["True", "1", "true"])].copy()
    df["source"] = source
    df["horizon"] = df.get("horizon", 1)
    return df


def read_output_files(folder: pathlib.Path) -> dict[str, dict[pd.Timestamp, float]]:
    by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    if not folder.exists():
        return by_fund
    for path in sorted(folder.glob("*.csv")):
        parts = path.stem.split("__", 1)
        if len(parts) != 2:
            continue
        ticker, _ = parts
        df = pd.read_csv(path, skiprows=12)
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        col = df.columns[1]
        values = dict(zip(df["Date"], df[col]))
        by_fund.setdefault(ticker, {}).update(values)
    return by_fund


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p1 = load_validated(OUT_DIR / "sparse_relaxed_validation.csv", "P1_relaxed", "holdout_pass_0_2")
    p1 = p1[p1["reliable"].astype(str).isin(["True", "1", "true"])].copy()
    p2 = load_validated(OUT_DIR / "mapping_composite_validation.csv", "P2_mapping", "pass_and_reliable")
    p3 = load_validated(OUT_DIR / "multi_day_validation.csv", "P3_multiday", "pass_and_reliable")
    p4a = load_validated(OUT_DIR / "self_signal_results.csv", "P4_self", "pass_and_reliable")
    p4b = load_validated(OUT_DIR / "external_signal_results.csv", "P4_external", "pass_and_reliable")

    cols = ["ticker", "fund_group", "source", "condition", "horizon", "holdout_trades", "holdout_hit_rate", "holdout_avg"]
    all_validated = pd.concat([p1, p2, p3, p4a, p4b], ignore_index=True)[cols]
    all_validated.to_csv(ALL_VALIDATED, index=False)

    fund = wf.load_panel(wf.FUND_PANEL)
    by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    for folder in [
        OUT_DIR / "sparse_outputs",
        OUT_DIR / "sparse_outputs_self",
        OUT_DIR / "sparse_outputs_external",
    ]:
        for ticker, values in read_output_files(folder).items():
            by_fund.setdefault(ticker, {}).update(values)

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

    main_stable = pd.read_csv(OUT_DIR / "stable_combos.csv")
    main_funds = set(main_stable["ticker"])
    sparse_funds = set(by_fund)
    total_covered = len(main_funds | sparse_funds)

    print(f"Validated sparse combos: {len(all_validated)}")
    print(all_validated.groupby("source")["ticker"].nunique().to_dict())
    print(f"Sparse funds with 1-day signals: {len(sparse_funds)}")
    print(f"Main stable funds: {len(main_funds)}")
    print(f"Total funds covered (main + sparse): {total_covered} / {len(all_tickers)}")
    print(f"New funds from sparse work: {len(sparse_funds)}")
    print(f"Daily union trigger cells: {sum(len(v) for v in by_fund_full.values())}")
    print(f"Saved: {ALL_VALIDATED}")
    print(f"Saved: {DAILY_OUT}")
    print(f"Saved: {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
