"""Frozen holdout: select combos on pre-2025 data, evaluate on 2025-2026."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pandas as pd

import scan_magnitude_bins as bins_mod
import scan_pair_events as pair_mod
import scan_single_events as single_mod
import walk_forward as wf


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
REPORT = OUT_DIR / "holdout_report.csv"

CUTOFF = datetime(2025, 1, 1)
SELECTION_PERIODS = [
    "2009-2012",
    "2013-2016",
    "2017-2020",
    "2021-2023",
]
MIN_PERIOD_TRADES = 10
MIN_OVERALL_TRADES = 50
MIN_PASS_PERIODS = 3
MIN_HOLDOUT_TRADES = 10


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fund = wf.load_panel(wf.FUND_PANEL)
    etf = wf.load_panel(wf.ETF_PANEL)
    cond_map = wf.build_condition_map(etf)

    combos: set[tuple[str, str]] = set()
    for short_path in (single_mod.SHORTLIST, pair_mod.SHORTLIST, bins_mod.SHORTLIST):
        short = pd.read_csv(short_path)
        passed = short[short["decision"] != "no_trade"]
        combos.update(zip(passed["ticker"], passed["condition"]))

    report_rows: list[dict] = []
    for ticker, condition in sorted(combos):
        trades = wf.evaluate_combo(
            cond_map[condition],
            fund[ticker].shift(-1),
            fund["Date"],
        )
        if not trades:
            continue

        selection_trades = [t for t in trades if t["date"].to_pydatetime() < CUTOFF]
        if not selection_trades:
            continue

        period_passes = 0
        for period in SELECTION_PERIODS:
            group = [t for t in selection_trades if wf.period_of(t["date"]) == period]
            if len(group) >= MIN_PERIOD_TRADES:
                avg = sum(t["actual"] for t in group) / len(group)
                if avg >= 0.2 or avg <= -0.2:
                    period_passes += 1

        selection_avg = sum(t["actual"] for t in selection_trades) / len(selection_trades)
        selection_pass = (
            len(selection_trades) >= MIN_OVERALL_TRADES
            and (selection_avg >= 0.2 or selection_avg <= -0.2)
            and period_passes >= MIN_PASS_PERIODS
        )

        holdout_trades = [t for t in trades if t["date"].to_pydatetime() >= CUTOFF]
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
        holdout_pass = (
            len(holdout_trades) >= MIN_HOLDOUT_TRADES
            and (holdout_avg >= 0.2 or holdout_avg <= -0.2)
        )

        report_rows.append(
            {
                "ticker": ticker,
                "condition": condition,
                "selection_trades": len(selection_trades),
                "selection_avg": round(selection_avg, 4),
                "periods_passed": period_passes,
                "selected": selection_pass,
                "holdout_trades": len(holdout_trades),
                "holdout_hit_rate": round(holdout_hit, 4),
                "holdout_avg": round(holdout_avg, 4),
                "holdout_pass": holdout_pass,
            }
        )

    report = pd.DataFrame(report_rows)
    report = report.sort_values("holdout_avg", key=lambda s: s.abs(), ascending=False)
    report.to_csv(REPORT, index=False)

    selected = report[report["selected"]]
    holdout_passed = selected[selected["holdout_pass"]]
    print(f"Combos evaluated: {len(report)}")
    print(f"Selected on pre-2025 data: {len(selected)}")
    print(f"Holdout passed (2025-2026): {len(holdout_passed)}")
    if not selected.empty:
        rate = len(holdout_passed) / len(selected) * 100
        print(f"Holdout pass rate: {rate:.1f}%")
    if not holdout_passed.empty:
        cols = ["ticker", "condition", "selection_trades", "selection_avg", "periods_passed", "holdout_trades", "holdout_hit_rate", "holdout_avg", "holdout_pass"]
        print(holdout_passed[cols].head(20).to_string(index=False))
    print(f"Saved: {REPORT}")


if __name__ == "__main__":
    main()
