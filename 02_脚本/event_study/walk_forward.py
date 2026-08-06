"""Walk-forward validation: decisions only use history before each event date."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pandas as pd

import scan_magnitude_bins as bins_mod
import scan_pair_events as pair_mod
import scan_single_events as single_mod


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
ETF_PANEL = OUT_DIR / "panel_etf_returns.csv"
STABILITY_REPORT = OUT_DIR / "stability_report.csv"
VALIDATION_SUMMARY = OUT_DIR / "validation_summary.csv"
STABLE_COMBOS = OUT_DIR / "stable_combos.csv"

PERIODS = [
    ("2009-2012", datetime(2009, 1, 1), datetime(2012, 12, 31)),
    ("2013-2016", datetime(2013, 1, 1), datetime(2016, 12, 31)),
    ("2017-2020", datetime(2017, 1, 1), datetime(2020, 12, 31)),
    ("2021-2023", datetime(2021, 1, 1), datetime(2023, 12, 31)),
    ("2024-2026", datetime(2024, 1, 1), datetime(2026, 12, 31)),
]

MIN_N = 100
MIN_P = 0.55
MIN_ABS = 0.2
MIN_PERIOD_TRADES = 10
MIN_OVERALL_TRADES = 50
MIN_PASS_PERIODS = 3


def load_panel(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def build_condition_map(etf: pd.DataFrame) -> dict[str, pd.Series]:
    cond_map: dict[str, pd.Series] = {}
    for name, mask in single_mod.build_conditions(etf):
        cond_map[name] = mask
    for name, mask in pair_mod.build_conditions(etf):
        cond_map[name] = mask
    for name, mask in bins_mod.build_conditions(etf):
        cond_map[name] = mask
    return cond_map


def decide(
    n: int,
    up: int,
    down: int,
    sum_up: float,
    sum_down: float,
) -> tuple[str, float]:
    if n >= MIN_N:
        p_up = up / n
        p_down = down / n
        avg_up = sum_up / up if up else float("nan")
        avg_down = sum_down / down if down else float("nan")
        if p_up >= MIN_P and avg_up >= MIN_ABS:
            return "predict_up", avg_up
        if p_down >= MIN_P and avg_down <= -MIN_ABS:
            return "predict_down", avg_down
    return "no_trade", float("nan")


def evaluate_combo(
    mask: pd.Series,
    tomorrow: pd.Series,
    dates: pd.Series,
) -> list[dict]:
    events = pd.DataFrame({"date": dates[mask], "actual": tomorrow[mask]})
    events = events.dropna().sort_values("date")

    trades: list[dict] = []
    n = 0
    up = 0
    down = 0
    sum_up = 0.0
    sum_down = 0.0
    for event_date, actual in zip(events["date"], events["actual"]):
        decision, predicted = decide(n, up, down, sum_up, sum_down)
        actual_pct = float(actual) * 100
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


def period_of(date: pd.Timestamp) -> str:
    for name, start, end in PERIODS:
        if start <= date.to_pydatetime() <= end:
            return name
    return "before-2009"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fund = load_panel(FUND_PANEL)
    etf = load_panel(ETF_PANEL)
    cond_map = build_condition_map(etf)

    combos: set[tuple[str, str]] = set()
    for short_path in (single_mod.SHORTLIST, pair_mod.SHORTLIST, bins_mod.SHORTLIST):
        short = pd.read_csv(short_path)
        passed = short[short["decision"] != "no_trade"]
        combos.update(zip(passed["ticker"], passed["condition"]))

    stability_rows: list[dict] = []
    summary_rows: list[dict] = []
    for ticker, condition in sorted(combos):
        trades = evaluate_combo(
            cond_map[condition],
            fund[ticker].shift(-1),
            fund["Date"],
        )
        if not trades:
            continue

        trades_by_period: dict[str, list[dict]] = {}
        for trade in trades:
            trades_by_period.setdefault(period_of(trade["date"]), []).append(trade)

        period_passes = 0
        for name, _, _ in PERIODS:
            group = trades_by_period.get(name, [])
            n_trades = len(group)
            if not group:
                stability_rows.append(
                    {
                        "ticker": ticker,
                        "condition": condition,
                        "period": name,
                        "trades": 0,
                        "hit_rate": "",
                        "avg_actual": "",
                        "pass": "",
                    }
                )
                continue
            actuals = pd.Series([t["actual"] for t in group])
            avg = float(actuals.mean())
            hit = float((actuals * pd.Series([1 if t["decision"] == "predict_up" else -1 for t in group]) > 0).mean())
            period_pass = n_trades >= MIN_PERIOD_TRADES and (avg >= MIN_ABS or avg <= -MIN_ABS)
            period_passes += int(period_pass)
            stability_rows.append(
                {
                    "ticker": ticker,
                    "condition": condition,
                    "period": name,
                    "trades": n_trades,
                    "hit_rate": round(hit, 4),
                    "avg_actual": round(avg, 4),
                    "pass": period_pass,
                }
            )

        all_actuals = pd.Series([t["actual"] for t in trades])
        overall_trades = len(all_actuals)
        overall_avg = float(all_actuals.mean())
        overall_pass = (
            overall_trades >= MIN_OVERALL_TRADES
            and (overall_avg >= MIN_ABS or overall_avg <= -MIN_ABS)
        )
        stable = overall_pass and period_passes >= MIN_PASS_PERIODS
        summary_rows.append(
            {
                "ticker": ticker,
                "condition": condition,
                "overall_trades": overall_trades,
                "overall_avg": round(overall_avg, 4),
                "periods_passed": period_passes,
                "overall_pass": overall_pass,
                "stable": stable,
            }
        )

    stability = pd.DataFrame(stability_rows)
    stability.to_csv(STABILITY_REPORT, index=False)
    summary = pd.DataFrame(summary_rows)
    summary = summary.sort_values("overall_avg", key=lambda s: s.abs(), ascending=False)
    summary.to_csv(VALIDATION_SUMMARY, index=False)
    stable = summary[summary["stable"]]
    stable.to_csv(STABLE_COMBOS, index=False)

    print(f"Combos evaluated: {len(summary_rows)}")
    print(f"Stable combos: {len(stable)}")
    if not stable.empty:
        print(stable.to_string(index=False))
    print(f"Saved: {STABILITY_REPORT}")
    print(f"Saved: {VALIDATION_SUMMARY}")
    print(f"Saved: {STABLE_COMBOS}")


if __name__ == "__main__":
    main()
