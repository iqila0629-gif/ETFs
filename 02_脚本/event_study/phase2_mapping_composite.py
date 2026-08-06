"""Phase 2: fund-specific ETF mapping (M2) and composite conditions (M3)."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import walk_forward as wf
from generate_predictions import write_standard_csv
from phase1_relaxed_validation import (
    CUTOFF,
    MIN_ABS,
    MIN_P,
    SELECTION_PERIODS,
    SHORT_OBS,
    evaluate_relaxed,
    period_passes,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
DIAGNOSIS = OUT_DIR / "target_funds_diagnosis.csv"
REPORT = OUT_DIR / "mapping_composite_validation.csv"
OUTPUTS = OUT_DIR / "sparse_outputs"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    diagnosis = pd.read_csv(DIAGNOSIS, keep_default_na=False)

    fund = wf.load_panel(wf.FUND_PANEL)
    etf = wf.load_panel(wf.ETF_PANEL)
    cond_map = wf.build_condition_map(etf)
    etf_cols = list(etf.columns[1:])

    report_rows = []
    generated = 0
    skipped = 0
    for _, row in diagnosis.iterrows():
        ticker = str(row["ticker"])
        best_etf = str(row["best_etf"]).strip()
        if not best_etf:
            skipped += 1
            continue
        obs = int(row["obs"])
        short = obs < SHORT_OBS
        min_n = 50 if short else 100
        min_period_trades = 5 if short else 10
        min_overall = 30 if short else 50
        min_pass_periods = 2 if short else 3
        min_holdout = 5 if short else 10
        market = "QQQ" if best_etf == "SPY" else "SPY"

        m2_names = [
            f"{best_etf}_up",
            f"{best_etf}_down",
            f"{best_etf}_big_up",
            f"{best_etf}_big_down",
            f"{best_etf}_bin_gt2",
            f"{best_etf}_bin_lt-2",
        ]
        e = etf[best_etf]
        m = etf[market]
        m3_conditions = [
            (f"{best_etf}_up_{market}_up", (e > 0) & (m > 0)),
            (f"{best_etf}_down_{market}_down", (e < 0) & (m < 0)),
            (f"{best_etf}_up_{market}_down", (e > 0) & (m < 0)),
            (f"{best_etf}_down_{market}_up", (e < 0) & (m > 0)),
        ]

        for method, condition, mask in [
            ("M2", name, cond_map[name]) for name in m2_names
        ] + [("M3", name, mask) for name, mask in m3_conditions]:
            trades = evaluate_relaxed(
                mask,
                fund[ticker].shift(-1),
                fund["Date"],
                min_n,
                MIN_P,
                MIN_ABS,
            )
            if not trades:
                continue

            selection_trades = [t for t in trades if t["date"].to_pydatetime() < CUTOFF]
            holdout_trades = [t for t in trades if t["date"].to_pydatetime() >= CUTOFF]
            selection_avg = (
                sum(t["actual"] for t in selection_trades) / len(selection_trades)
                if selection_trades
                else float("nan")
            )
            selected = (
                len(selection_trades) >= min_overall
                and (selection_avg >= MIN_ABS or selection_avg <= -MIN_ABS)
                and period_passes(selection_trades, SELECTION_PERIODS, min_period_trades) >= min_pass_periods
            )
            holdout_avg = (
                sum(t["actual"] for t in holdout_trades) / len(holdout_trades)
                if holdout_trades
                else float("nan")
            )
            holdout_hit = (
                sum(
                    1
                    for t in holdout_trades
                    if (t["decision"] == "predict_up" and t["actual"] > 0)
                    or (t["decision"] == "predict_down" and t["actual"] < 0)
                )
                / len(holdout_trades)
                if holdout_trades
                else float("nan")
            )
            pass_and_reliable = (
                len(holdout_trades) >= min_holdout
                and holdout_hit == holdout_hit
                and holdout_hit >= 0.45
                and (holdout_avg >= 0.2 or holdout_avg <= -0.2)
            )
            report_rows.append(
                {
                    "ticker": ticker,
                    "fund_group": row["fund_group"],
                    "obs": obs,
                    "best_etf": best_etf,
                    "best_corr": row["best_corr"],
                    "method": method,
                    "condition": condition,
                    "short_history": short,
                    "selection_trades": len(selection_trades),
                    "selection_avg": round(selection_avg, 4),
                    "selected_pre2025": selected,
                    "holdout_trades": len(holdout_trades),
                    "holdout_hit_rate": round(holdout_hit, 4),
                    "holdout_avg": round(holdout_avg, 4),
                    "pass_and_reliable": pass_and_reliable,
                }
            )

            if pass_and_reliable:
                rows = [
                    (t["date"].strftime("%m/%d/%Y"), t["actual"])
                    for t in sorted(trades, key=lambda t: t["date"], reverse=True)
                ]
                path = OUTPUTS / f"{ticker}__{condition}.csv"
                write_standard_csv(path, rows)
                generated += 1

    report = pd.DataFrame(report_rows)
    if not report.empty:
        report = report.sort_values("holdout_avg", key=lambda s: s.abs(), ascending=False)
    report.to_csv(REPORT, index=False)

    passed = report[report["pass_and_reliable"]] if not report.empty else report
    print(f"Target funds: {len(diagnosis)}")
    print(f"Skipped (no ETF mapping): {skipped}")
    print(f"Combos evaluated: {len(report)}")
    print(f"Pass and reliable: {len(passed)}")
    print(f"Distinct funds passed: {passed['ticker'].nunique() if not passed.empty else 0}")
    if not passed.empty:
        cols = ["ticker", "method", "condition", "best_etf", "holdout_trades", "holdout_hit_rate", "holdout_avg"]
        print(passed[cols].head(25).to_string(index=False))
    print(f"Prediction CSVs generated: {generated}")
    print(f"Saved: {REPORT}")
    print(f"Saved to: {OUTPUTS}")


if __name__ == "__main__":
    main()
