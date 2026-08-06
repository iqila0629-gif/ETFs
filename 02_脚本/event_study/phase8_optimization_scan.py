"""Phase 8: check whether 57 new ETFs improve signals for existing funds."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import event_metrics as em
import walk_forward as wf
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
COMBINED_EXT = ROOT / "processed_returns" / "combined_extended_etf_returns.csv"
STABLE = OUT_DIR / "stable_combos.csv"
SPARSE_VALIDATED = OUT_DIR / "sparse_all_validated.csv"
EXTENDED_VALIDATION = OUT_DIR / "extended_etf_validation.csv"
BLANK_VALIDATION = OUT_DIR / "blank_funds_more_etf_validation.csv"
SCAN_OUT = OUT_DIR / "optimization_scan.csv"
SUMMARY_OUT = OUT_DIR / "optimization_summary.csv"

MIN_N = 100
MIN_P = 0.52
MIN_ABS = 0.15
CUTOFF = np.datetime64("2025-01-01")
PERIODS_NP = [
    ("2017-2020", np.datetime64("2017-01-01"), np.datetime64("2020-12-31")),
    ("2021-2023", np.datetime64("2021-01-01"), np.datetime64("2023-12-31")),
]
HORIZONS = [1, 2, 3]
EXCLUDED = {"MPIXX", "MPSXX"}


def multi_day_target(series: pd.Series, n: int) -> pd.Series:
    return pd.concat([series.shift(-k) for k in range(1, n + 1)], axis=1).mean(axis=1)


def evaluate_vectorized(
    mask: pd.Series,
    tomorrow: pd.Series,
    dates: pd.Series,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(tomorrow.to_numpy(dtype=float))
    ev_dates = dates.to_numpy()[valid]
    vals = tomorrow.to_numpy(dtype=float)[valid] * 100.0
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool), np.array([], dtype="U11"), np.array([], dtype=float)
    up_flag = vals > 0
    down_flag = vals < 0
    cum_n = np.arange(n, dtype=float)
    cum_up = np.concatenate([[0.0], np.cumsum(up_flag)[:-1]])
    cum_down = np.concatenate([[0.0], np.cumsum(down_flag)[:-1]])
    cum_su = np.concatenate([[0.0], np.cumsum(np.where(up_flag, vals, 0.0))[:-1]])
    cum_sd = np.concatenate([[0.0], np.cumsum(np.where(down_flag, vals, 0.0))[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_up = cum_up / cum_n
        p_down = cum_down / cum_n
        avg_up = cum_su / np.where(cum_up > 0, cum_up, 1)
        avg_down = cum_sd / np.where(cum_down > 0, cum_down, 1)
        dec_up = (cum_n >= MIN_N) & (p_up >= MIN_P) & (avg_up >= MIN_ABS)
        dec_down = (cum_n >= MIN_N) & (p_down >= MIN_P) & (avg_down <= -MIN_ABS)
    trade_mask = dec_up | dec_down
    decisions = np.where(dec_up, "predict_up", np.where(dec_down, "predict_down", "no_trade"))
    predicted = np.where(dec_up, avg_up, np.where(dec_down, avg_down, np.nan))
    return ev_dates, vals, trade_mask, decisions, predicted


def period_passes_vec(dates: np.ndarray, vals: np.ndarray) -> int:
    passes = 0
    for _, start, end in PERIODS_NP:
        m = (dates >= start) & (dates <= end)
        if int(m.sum()) >= 10:
            if abs(float(vals[m].mean())) >= MIN_ABS:
                passes += 1
    return passes


def existing_best() -> dict[str, dict]:
    best: dict[str, dict] = {}

    def update(ticker: str, avg: float, source: str) -> None:
        avg = pd.to_numeric(pd.Series([avg]), errors="coerce").iloc[0]
        if avg != avg:
            return
        if ticker not in best or abs(avg) > abs(best[ticker]["avg"]):
            best[ticker] = {"avg": avg, "source": source}

    stable = pd.read_csv(STABLE)
    for _, row in stable.iterrows():
        update(str(row["ticker"]), row["overall_avg"], "main")
    for path in [SPARSE_VALIDATED, EXTENDED_VALIDATION, BLANK_VALIDATION]:
        df = pd.read_csv(path, keep_default_na=False)
        if "pass_and_reliable" in df.columns:
            df = df[df["pass_and_reliable"].astype(str).isin(["True", "1", "true"])]
        for _, row in df.iterrows():
            update(str(row["ticker"]), row["holdout_avg"], path.stem)
    return best


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fund = wf.load_panel(FUND_PANEL)
    ext = pd.read_csv(COMBINED_EXT, skiprows=12)
    ext["Date"] = pd.to_datetime(ext["Date"], format="%m/%d/%Y")
    merged = fund.merge(ext, on="Date", how="inner").sort_values("Date").reset_index(drop=True)
    new_etfs = list(ext.columns[1:])

    existing = existing_best()
    scan_rows = []
    tickers = [t for t in fund.columns[1:] if t not in EXCLUDED]
    for i, ticker in enumerate(tickers):
        targets = {h: multi_day_target(merged[ticker], h) for h in HORIZONS}
        for etf in new_etfs:
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
                for h in HORIZONS:
                    ev_dates, vals, trade_mask, decisions, _ = evaluate_vectorized(
                        mask, targets[h], merged["Date"]
                    )
                    if not trade_mask.any():
                        continue
                    sel = trade_mask & (ev_dates < CUTOFF)
                    hold = trade_mask & (ev_dates >= CUTOFF)
                    sel_n = int(sel.sum())
                    hold_n = int(hold.sum())
                    if sel_n == 0 or hold_n == 0:
                        continue
                    sel_avg = float(vals[sel].mean())
                    hold_avg = float(vals[hold].mean())
                    hit = float(((decisions[hold] == "predict_up") & (vals[hold] > 0)).sum() / hold_n)
                    hit += float(((decisions[hold] == "predict_down") & (vals[hold] < 0)).sum() / hold_n)
                    selected = (
                        sel_n >= 50
                        and abs(sel_avg) >= MIN_ABS
                        and period_passes_vec(ev_dates[sel], vals[sel]) >= 1
                    )
                    pass_and_reliable = (
                        hold_n >= 10
                        and hit >= 0.45
                        and (hold_avg >= 0.2 or hold_avg <= -0.2)
                    )
                    if pass_and_reliable:
                        scan_rows.append(
                            {
                                "ticker": ticker,
                                "fund_group": em.fund_group(ticker),
                                "condition": condition,
                                "horizon": h,
                                "selection_trades": sel_n,
                                "selection_avg": round(sel_avg, 4),
                                "selected_pre2025": selected,
                                "holdout_trades": hold_n,
                                "holdout_hit_rate": round(hit, 4),
                                "holdout_avg": round(hold_avg, 4),
                            }
                        )
        if (i + 1) % 25 == 0:
            print(f"scanned {i + 1}/{len(tickers)} funds")

    scan = pd.DataFrame(scan_rows)
    if not scan.empty:
        scan = scan.sort_values("holdout_avg", key=lambda s: s.abs(), ascending=False)
    scan.to_csv(SCAN_OUT, index=False)

    summary_rows = []
    if not scan.empty:
        for ticker, group in scan.groupby("ticker"):
            row = group.reindex(group["holdout_avg"].abs().sort_values(ascending=False).index).iloc[0]
            old = existing.get(ticker, {"avg": float("nan"), "source": ""})
            improvement = abs(row["holdout_avg"]) > abs(old["avg"]) if old["avg"] == old["avg"] else True
            summary_rows.append(
                {
                    "ticker": ticker,
                    "fund_group": row["fund_group"],
                    "existing_best_avg": round(old["avg"], 4) if old["avg"] == old["avg"] else "",
                    "existing_best_source": old["source"],
                    "new_best_condition": row["condition"],
                    "new_horizon": row["horizon"],
                    "new_holdout_trades": row["holdout_trades"],
                    "new_holdout_hit_rate": row["holdout_hit_rate"],
                    "new_holdout_avg": row["holdout_avg"],
                    "improvement": improvement,
                }
            )
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary = summary.sort_values("new_holdout_avg", key=lambda s: s.abs(), ascending=False)
    summary.to_csv(SUMMARY_OUT, index=False)

    improved = summary[summary["improvement"]] if not summary.empty else summary
    print(f"Funds scanned: {len(tickers)}")
    print(f"New pass-and-reliable combos: {len(scan)}")
    print(f"Funds with new signals: {summary['ticker'].nunique() if not summary.empty else 0}")
    print(f"Funds improved vs existing best: {len(improved)}")
    if not improved.empty:
        cols = ["ticker", "existing_best_avg", "existing_best_source", "new_best_condition", "new_horizon", "new_holdout_trades", "new_holdout_hit_rate", "new_holdout_avg"]
        print(improved[cols].head(20).to_string(index=False))
    print(f"Saved: {SCAN_OUT}")
    print(f"Saved: {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
