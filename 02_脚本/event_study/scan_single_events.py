"""Scan single-ETF conditions against next-day fund returns."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

import event_metrics as em


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
ETF_PANEL = OUT_DIR / "panel_etf_returns.csv"
SUMMARY = OUT_DIR / "event_summary_single.csv"
SHORTLIST = OUT_DIR / "shortlist_single.csv"


def load_panel(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def build_conditions(etf: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    conditions = []
    for col in etf.columns[1:]:
        s = etf[col]
        conditions.append((f"{col}_up", s > 0))
        conditions.append((f"{col}_down", s < 0))
        conditions.append((f"{col}_big_up", s >= 1.0))
        conditions.append((f"{col}_big_down", s <= -1.0))
    return conditions


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fund = load_panel(FUND_PANEL)
    etf = load_panel(ETF_PANEL)
    conditions = build_conditions(etf)
    tomorrow_by_fund = {
        col: fund[col].shift(-1) for col in fund.columns[1:]
    }

    rows = []
    for cond_name, mask in conditions:
        for ticker, tomorrow in tomorrow_by_fund.items():
            metrics = em.condition_metrics(mask, tomorrow)
            rows.append(
                {
                    "ticker": ticker,
                    "fund_group": em.fund_group(ticker),
                    "condition": cond_name,
                    **metrics,
                }
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY, index=False)

    short = em.shortlist(summary)
    short = em.add_decision(short)
    short = short.sort_values("expected", key=lambda s: s.abs(), ascending=False)
    short.to_csv(SHORTLIST, index=False)

    print(f"Conditions: {len(conditions)}, fund-condition rows: {len(summary)}")
    print(f"Shortlist rows: {len(short)}")
    passed = short[short["decision"] != "no_trade"]
    print(f"Strict-rule passes: {len(passed)}")
    if not passed.empty:
        cols = ["ticker", "condition", "n", "p_up", "p_down", "avg_up", "avg_down", "expected", "decision", "predicted_return"]
        print(passed.sort_values("expected", key=lambda s: s.abs(), ascending=False).head(20)[cols].to_string(index=False))
    print(f"Saved: {SUMMARY}")
    print(f"Saved: {SHORTLIST}")


if __name__ == "__main__":
    main()
