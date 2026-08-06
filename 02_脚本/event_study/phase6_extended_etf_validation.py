"""Phase 6: validate extended ETF conditions for the remaining uncovered funds."""

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
    evaluate_relaxed,
    period_passes,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
COMBINED_EXT = ROOT / "processed_returns" / "combined_extended_etf_returns.csv"
REPORT = OUT_DIR / "extended_etf_validation.csv"
OUTPUTS = OUT_DIR / "sparse_outputs_extended"

TARGET_FUNDS = ["GVPIX", "RDPIX", "RDPSX", "RRPIX", "RRPSX", "RTPIX", "RTPSX"]
SELECTION_PERIODS = ["2017-2020", "2021-2023"]
NEW_ETFS = [
    "IEF", "SHY", "BIL", "TMF", "TMV", "ZROZ", "EDV", "MUB",
    "UDN", "FXE", "CEW", "GDXJ", "IAU", "XME", "DBC", "VGSH",
    "VCLT", "VCIT", "MBB", "SCHP", "FLRN", "FXB", "SIL", "COPX",
    "USO", "XLB", "XLY", "XLP", "XLC", "XBI",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    fund = wf.load_panel(FUND_PANEL)
    ext = pd.read_csv(COMBINED_EXT, skiprows=12)
    ext["Date"] = pd.to_datetime(ext["Date"], format="%m/%d/%Y")
    merged = fund.merge(ext, on="Date", how="inner").sort_values("Date").reset_index(drop=True)

    report_rows = []
    generated = 0
    for ticker in TARGET_FUNDS:
        tomorrow = merged[ticker].shift(-1)
        for etf in NEW_ETFS:
            s = merged[etf]
            conditions = [
                (f"{etf}_up", s > 0),
                (f"{etf}_down", s < 0),
                (f"{etf}_big_up", s >= 1.0),
                (f"{etf}_big_down", s <= -1.0),
                (f"{etf}_gt2", s > 2.0),
                (f"{etf}_lt-2", s < -2.0),
            ]
            for condition, mask in conditions:
                trades = evaluate_relaxed(mask, tomorrow, merged["Date"], 100, MIN_P, MIN_ABS)
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
                    len(selection_trades) >= 50
                    and (selection_avg >= MIN_ABS or selection_avg <= -MIN_ABS)
                    and period_passes(selection_trades, SELECTION_PERIODS, 10) >= 1
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
                    len(holdout_trades) >= 10
                    and holdout_hit == holdout_hit
                    and holdout_hit >= 0.45
                    and (holdout_avg >= 0.2 or holdout_avg <= -0.2)
                )
                report_rows.append(
                    {
                        "ticker": ticker,
                        "condition": condition,
                        "selection_trades": len(selection_trades),
                        "selection_avg": round(selection_avg, 4),
                        "periods_passed": period_passes(selection_trades, SELECTION_PERIODS, 10),
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

    print(f"Funds targeted: {len(TARGET_FUNDS)}")
    print(f"Combos evaluated: {len(report)}")
    print(f"Pass and reliable: {len(passed)}")
    print(f"Distinct funds passed: {passed['ticker'].nunique() if not passed.empty else 0}")
    if not passed.empty:
        cols = ["ticker", "condition", "holdout_trades", "holdout_hit_rate", "holdout_avg"]
        print(passed[cols].head(20).to_string(index=False))
    print(f"Prediction CSVs generated: {generated}")
    print(f"Saved: {REPORT}")
    print(f"Saved to: {OUTPUTS}")


if __name__ == "__main__":
    main()
