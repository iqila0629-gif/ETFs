"""Phase 1: relaxed-rule walk-forward + frozen holdout for sparse/no-trigger funds."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pandas as pd

import walk_forward as wf
from generate_predictions import write_standard_csv


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
DIAGNOSIS = OUT_DIR / "target_funds_diagnosis.csv"
REPORT = OUT_DIR / "sparse_relaxed_validation.csv"
OUTPUTS = OUT_DIR / "sparse_outputs"

CUTOFF = datetime(2025, 1, 1)
SELECTION_PERIODS = ["2009-2012", "2013-2016", "2017-2020", "2021-2023"]
MIN_P = 0.52
MIN_ABS = 0.15
SHORT_OBS = 1000


def evaluate_relaxed(
    mask: pd.Series,
    tomorrow: pd.Series,
    dates: pd.Series,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> list[dict]:
    """Expanding-window decisions under the relaxed M1 rule."""
    events = pd.DataFrame({"date": dates[mask], "actual": tomorrow[mask]})
    events = events.dropna().sort_values("date")
    trades: list[dict] = []
    n = 0
    up = 0
    down = 0
    sum_up = 0.0
    sum_down = 0.0
    for event_date, actual in zip(events["date"], events["actual"]):
        actual_pct = float(actual) * 100
        decision = "no_trade"
        predicted = float("nan")
        if n >= min_n:
            p_up = up / n
            p_down = down / n
            avg_up = sum_up / up if up else float("nan")
            avg_down = sum_down / down if down else float("nan")
            if p_up >= min_p and avg_up >= min_abs:
                decision = "predict_up"
                predicted = avg_up
            elif p_down >= min_p and avg_down <= -min_abs:
                decision = "predict_down"
                predicted = avg_down
        if decision != "no_trade":
            trades.append(
                {
                    "date": event_date,
                    "actual": actual_pct,
                    "decision": decision,
                    "predicted": predicted,
                }
            )
        n += 1
        if actual_pct > 0:
            up += 1
            sum_up += actual_pct
        elif actual_pct < 0:
            down += 1
            sum_down += actual_pct
    return trades


def period_passes(trades: list[dict], periods: list[str], min_trades: int) -> int:
    passes = 0
    for name in periods:
        group = [t for t in trades if wf.period_of(t["date"]) == name]
        if len(group) >= min_trades:
            avg = sum(t["actual"] for t in group) / len(group)
            if avg >= MIN_ABS or avg <= -MIN_ABS:
                passes += 1
    return passes


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    diagnosis = pd.read_csv(DIAGNOSIS)
    candidates = diagnosis[diagnosis["relaxed_trigger"]]

    fund = wf.load_panel(wf.FUND_PANEL)
    etf = wf.load_panel(wf.ETF_PANEL)
    cond_map = wf.build_condition_map(etf)
    quality = pd.read_csv(wf.OUT_DIR / "panel_quality_report.csv").set_index("ticker")

    report_rows = []
    generated = 0
    for _, row in candidates.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["best_condition"])
        obs = int(row["obs"])
        short = obs < SHORT_OBS
        min_n = 50 if short else 100
        min_period_trades = 5 if short else 10
        min_overall = 30 if short else 50
        min_pass_periods = 2 if short else 3
        min_holdout = 5 if short else 10

        trades = evaluate_relaxed(
            cond_map[condition],
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

        overall_avg = sum(t["actual"] for t in trades) / len(trades)
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
        pass_0_2 = (
            len(holdout_trades) >= min_holdout
            and (holdout_avg >= 0.2 or holdout_avg <= -0.2)
        )
        pass_0_15 = (
            len(holdout_trades) >= min_holdout
            and (holdout_avg >= 0.15 or holdout_avg <= -0.15)
        )
        reliable = holdout_hit == holdout_hit and holdout_hit >= 0.45

        report_rows.append(
            {
                "ticker": ticker,
                "fund_group": row["fund_group"],
                "condition": condition,
                "obs": obs,
                "short_history": short,
                "selection_trades": len(selection_trades),
                "selection_avg": round(selection_avg, 4),
                "periods_passed": period_passes(selection_trades, SELECTION_PERIODS, min_period_trades),
                "selected_pre2025": selected,
                "overall_trades": len(trades),
                "overall_avg": round(overall_avg, 4),
                "holdout_trades": len(holdout_trades),
                "holdout_hit_rate": round(holdout_hit, 4),
                "holdout_avg": round(holdout_avg, 4),
                "holdout_pass_0_2": pass_0_2,
                "holdout_pass_0_15": pass_0_15,
                "reliable": reliable,
            }
        )

        if pass_0_2 and reliable:
            rows = [
                (t["date"].strftime("%m/%d/%Y"), t["actual"])
                for t in sorted(trades, key=lambda t: t["date"], reverse=True)
            ]
            path = OUTPUTS / f"{ticker}__{condition}.csv"
            write_standard_csv(path, rows)
            generated += 1

    report = pd.DataFrame(report_rows)
    report = report.sort_values("holdout_avg", key=lambda s: s.abs(), ascending=False)
    report.to_csv(REPORT, index=False)

    print(f"Candidates: {len(candidates)}")
    print(f"Evaluated: {len(report)}")
    print(f"Selected on pre-2025 data: {report['selected_pre2025'].sum()}")
    print(f"Holdout pass >=0.2%: {report['holdout_pass_0_2'].sum()}")
    print(f"Holdout pass >=0.15%: {report['holdout_pass_0_15'].sum()}")
    print(f"Holdout pass >=0.2% and reliable: {len(report[report['holdout_pass_0_2'] & report['reliable']])}")
    print(f"Prediction CSVs generated: {generated}")
    final = report[report["holdout_pass_0_2"] & report["reliable"]]
    if not final.empty:
        cols = ["ticker", "condition", "obs", "short_history", "holdout_trades", "holdout_hit_rate", "holdout_avg", "reliable"]
        print(final[cols].to_string(index=False))
    print(f"Saved: {REPORT}")
    print(f"Saved to: {OUTPUTS}")


if __name__ == "__main__":
    main()
