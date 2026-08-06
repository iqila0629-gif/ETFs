"""Generate company-format prediction CSVs for walk-forward stable combos."""

from __future__ import annotations

import csv
import pathlib
import sys

import pandas as pd

import walk_forward as wf


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
PREDICTIONS_DIR = OUT_DIR / "predictions"
STABLE = OUT_DIR / "stable_combos.csv"
LOG = OUT_DIR / "prediction_log.csv"


def write_standard_csv(path: pathlib.Path, rows: list[tuple[str, float]]) -> None:
    """Write the company 13-line format; Average is checked by the caller."""
    values = pd.Series([value for _, value in rows])
    count = int(values.count())
    up = int((values > 0).sum())
    down = int((values < 0).sum())
    hit = up / (up + down) if (up + down) else float("nan")
    std = float(values.std(ddof=1)) if count > 1 else float("nan")

    def fmt(value: float) -> str:
        return "" if value != value else f"{value:.6f}"

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([])
        writer.writerow(["Hit Ratio", fmt(hit)])
        writer.writerow(["Up Count", up])
        writer.writerow(["Down Count", down])
        writer.writerow(["Average", fmt(float(values.mean()))])
        writer.writerow(["Max", fmt(float(values.max()))])
        writer.writerow(["Min", fmt(float(values.min()))])
        writer.writerow(["Count", count])
        writer.writerow(["Std", fmt(std)])
        writer.writerow(["Sum", fmt(float(values.sum()))])
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Date", "Daily Return (%)"])
        for date_str, value in rows:
            writer.writerow([date_str, f"{value:.6f}"])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stable = pd.read_csv(STABLE)
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    fund = wf.load_panel(wf.FUND_PANEL)
    etf = wf.load_panel(wf.ETF_PANEL)
    cond_map = wf.build_condition_map(etf)

    log_rows: list[dict] = []
    generated = 0
    passed_check = 0
    failed: list[str] = []
    for _, combo in stable.iterrows():
        ticker = str(combo["ticker"])
        condition = str(combo["condition"])
        trades = wf.evaluate_combo(
            cond_map[condition],
            fund[ticker].shift(-1),
            fund["Date"],
        )
        if not trades:
            failed.append(f"{ticker}__{condition}: no trades")
            continue

        rows = [
            (trade["date"].strftime("%m/%d/%Y"), trade["actual"])
            for trade in sorted(trades, key=lambda t: t["date"], reverse=True)
        ]
        path = PREDICTIONS_DIR / f"{ticker}__{condition}.csv"
        write_standard_csv(path, rows)
        generated += 1

        average = sum(trade["actual"] for trade in trades) / len(trades)
        if average >= 0.2 or average <= -0.2:
            passed_check += 1
        else:
            failed.append(f"{ticker}__{condition}: average {average:.4f} below threshold")

        for trade in trades:
            log_rows.append(
                {
                    "ticker": ticker,
                    "condition": condition,
                    "date": trade["date"].strftime("%m/%d/%Y"),
                    "decision": trade["decision"],
                    "predicted_return": trade["predicted"],
                    "actual_return": trade["actual"],
                }
            )

    log = pd.DataFrame(log_rows)
    log.to_csv(LOG, index=False)

    print(f"Stable combos: {len(stable)}")
    print(f"Generated CSVs: {generated}")
    print(f"Average check passed: {passed_check}")
    print(f"Problems: {len(failed)}")
    for message in failed[:20]:
        print(f"  {message}")
    print(f"Saved to: {PREDICTIONS_DIR}")
    print(f"Saved log: {LOG}")


if __name__ == "__main__":
    main()
