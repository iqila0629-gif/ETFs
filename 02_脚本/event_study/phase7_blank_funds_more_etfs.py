"""Phase 7: search signals for the last blank funds with 57 ETFs + horizons."""

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
REPORT = OUT_DIR / "blank_funds_more_etf_validation.csv"
OUTPUTS = OUT_DIR / "sparse_outputs_blank_funds"

TARGET_FUNDS = ["GVPIX", "RDPIX", "RDPSX", "RTPIX", "RTPSX"]
SELECTION_PERIODS = ["2017-2020", "2021-2023"]
HORIZONS = [1, 2, 3, 5]


def multi_day_target(series: pd.Series, n: int) -> pd.Series:
    return pd.concat([series.shift(-k) for k in range(1, n + 1)], axis=1).mean(axis=1)


def build_composites(df: pd.DataFrame, fund: str) -> list[tuple[str, pd.Series]]:
    if fund in ("GVPIX",):
        pairs = [
            ("TMF_up_TMV_up", "TMF", "TMV", "up", "up"),
            ("TMF_down_TMV_down", "TMF", "TMV", "down", "down"),
            ("TMF_up_SPY_up", "TMF", "SPY", "up", "up"),
            ("TMF_down_SPY_down", "TMF", "SPY", "down", "down"),
            ("TMF_up_TLT_up", "TMF", "TLT", "up", "up"),
            ("TMF_down_TLT_down", "TMF", "TLT", "down", "down"),
        ]
    elif fund in ("RDPIX", "RDPSX"):
        pairs = [
            ("UUP_up_UDN_down", "UUP", "UDN", "up", "down"),
            ("UUP_down_UDN_up", "UUP", "UDN", "down", "up"),
            ("UUP_up_FXE_down", "UUP", "FXE", "up", "down"),
            ("UUP_down_FXE_up", "UUP", "FXE", "down", "up"),
            ("UUP_up_EUO_up", "UUP", "EUO", "up", "up"),
            ("UUP_down_EUO_down", "UUP", "EUO", "down", "down"),
        ]
    else:
        pairs = [
            ("TMV_up_TLT_down", "TMV", "TLT", "up", "down"),
            ("TMV_down_TLT_up", "TMV", "TLT", "down", "up"),
            ("TMV_up_IEF_down", "TMV", "IEF", "up", "down"),
            ("TMV_down_IEF_up", "TMV", "IEF", "down", "up"),
            ("TMV_up_TBT_up", "TMV", "TBT", "up", "up"),
            ("TMV_down_TBT_down", "TMV", "TBT", "down", "down"),
        ]

    conditions = []
    for name, a, b, sa, sb in pairs:
        mask_a = df[a] > 0 if sa == "up" else df[a] < 0
        mask_b = df[b] > 0 if sb == "up" else df[b] < 0
        conditions.append((name, mask_a & mask_b))
    return conditions


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    fund = wf.load_panel(FUND_PANEL)
    ext = pd.read_csv(COMBINED_EXT, skiprows=12)
    ext["Date"] = pd.to_datetime(ext["Date"], format="%m/%d/%Y")
    etf19 = wf.load_panel(wf.ETF_PANEL)
    merged = (
        fund.merge(etf19, on="Date", how="inner")
        .merge(ext, on="Date", how="inner")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    etf_list = list(ext.columns[1:])

    report_rows = []
    generated = 0
    for ticker in TARGET_FUNDS:
        single_conditions: list[tuple[str, pd.Series]] = []
        for etf in etf_list:
            s = merged[etf]
            single_conditions.extend(
                [
                    (f"{etf}_up", s > 0),
                    (f"{etf}_down", s < 0),
                    (f"{etf}_big_up", s >= 1.0),
                    (f"{etf}_big_down", s <= -1.0),
                    (f"{etf}_gt2", s > 2.0),
                    (f"{etf}_lt-2", s < -2.0),
                ]
            )
        conditions = single_conditions + build_composites(merged, ticker)

        for condition, mask in conditions:
            for n in HORIZONS:
                target = multi_day_target(merged[ticker], n)
                trades = evaluate_relaxed(mask, target, merged["Date"], 100, MIN_P, MIN_ABS)
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
                        "horizon": n,
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
                    name = f"{ticker}__{condition}" + (f"__N{n}" if n > 1 else "")
                    write_standard_csv(OUTPUTS / f"{name}.csv", rows)
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
        cols = ["ticker", "condition", "horizon", "holdout_trades", "holdout_hit_rate", "holdout_avg"]
        print(passed[cols].head(30).to_string(index=False))
    print(f"Prediction CSVs generated: {generated}")
    print(f"Saved: {REPORT}")
    print(f"Saved to: {OUTPUTS}")


if __name__ == "__main__":
    main()
