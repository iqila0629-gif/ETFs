"""Build a complete daily-frequency table: every trading day, one column per fund."""

from __future__ import annotations

import csv
import pathlib
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
DAILY_OUT = OUT_DIR / "daily_predictions_all_funds.csv"
SUMMARY_OUT = OUT_DIR / "daily_funds_summary.csv"
STABLE = OUT_DIR / "stable_combos.csv"


def fmt_number(value: float, is_count: bool = False) -> str:
    if value != value:
        return ""
    if is_count:
        return str(int(value))
    return f"{value:.6f}"


def write_daily_wide(path: pathlib.Path, dates: list[pd.Timestamp], tickers: list[str], by_fund: dict[str, dict[pd.Timestamp, float]]) -> None:
    """Company 13-line header plus one row per trading day (descending)."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([])
        for stat in ["Hit Ratio", "Up Count", "Down Count", "Average", "Max", "Min", "Count", "Std", "Sum"]:
            row = [stat]
            for ticker in tickers:
                values = pd.Series(list(by_fund.get(ticker, {}).values()), dtype="float64")
                if values.empty:
                    row.append("")
                    continue
                up = int((values > 0).sum())
                down = int((values < 0).sum())
                if stat == "Hit Ratio":
                    row.append(fmt_number(up / (up + down) if (up + down) else float("nan")))
                elif stat == "Up Count":
                    row.append(fmt_number(float(up), is_count=True))
                elif stat == "Down Count":
                    row.append(fmt_number(float(down), is_count=True))
                elif stat == "Average":
                    row.append(fmt_number(float(values.mean())))
                elif stat == "Max":
                    row.append(fmt_number(float(values.max())))
                elif stat == "Min":
                    row.append(fmt_number(float(values.min())))
                elif stat == "Count":
                    row.append(fmt_number(float(len(values)), is_count=True))
                elif stat == "Std":
                    row.append(fmt_number(float(values.std(ddof=1))) if len(values) > 1 else "")
                elif stat == "Sum":
                    row.append(fmt_number(float(values.sum())))
            writer.writerow(row)
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Date", *tickers])
        for date in dates:
            row = [date.strftime("%m/%d/%Y")]
            for ticker in tickers:
                value = by_fund.get(ticker, {}).get(date)
                row.append("" if value is None else f"{value:.6f}")
            writer.writerow(row)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stable = pd.read_csv(STABLE)
    fund = wf.load_panel(wf.FUND_PANEL)
    etf = wf.load_panel(wf.ETF_PANEL)
    cond_map = wf.build_condition_map(etf)

    all_tickers = list(fund.columns[1:])
    dates_desc = fund["Date"].sort_values(ascending=False).tolist()
    by_fund: dict[str, dict[pd.Timestamp, float]] = {ticker: {} for ticker in all_tickers}
    condition_count: dict[str, int] = {ticker: 0 for ticker in all_tickers}

    for _, combo in stable.iterrows():
        ticker = str(combo["ticker"])
        condition = str(combo["condition"])
        trades = wf.evaluate_combo(
            cond_map[condition],
            fund[ticker].shift(-1),
            fund["Date"],
        )
        if not trades:
            continue
        condition_count[ticker] += 1
        for trade in trades:
            by_fund[ticker].setdefault(trade["date"], trade["actual"])

    write_daily_wide(DAILY_OUT, dates_desc, all_tickers, by_fund)

    summary_rows = []
    for ticker in all_tickers:
        values = pd.Series(list(by_fund[ticker].values()), dtype="float64")
        if values.empty:
            continue
        up = int((values > 0).sum())
        summary_rows.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "conditions": condition_count[ticker],
                "trigger_days": int(len(values)),
                "hit_rate": round(up / len(values), 4),
                "average": round(float(values.mean()), 4),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("ticker")
    summary.to_csv(SUMMARY_OUT, index=False)

    print(f"Trading days in daily table: {len(dates_desc)}")
    print(f"Fund columns: {len(all_tickers)}")
    print(f"Funds with at least one trigger: {len(summary)}")
    print(f"Total trigger-day cells: {sum(len(v) for v in by_fund.values())}")
    print(f"Saved: {DAILY_OUT}")
    print(f"Saved: {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
