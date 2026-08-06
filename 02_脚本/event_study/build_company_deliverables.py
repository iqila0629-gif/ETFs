"""Build company-format integrated tables: best signal and all signals (R4)."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import walk_forward as wf
from generate_daily_tables import write_daily_wide
from phase9_dual_criteria_pipeline import (
    CUTOFF,
    build_master,
    build_masks,
    get_mask,
    get_target,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
DUAL = OUT_DIR / "dual_criteria_pass.csv"
SUMMARY = OUT_DIR / "dual_criteria_summary.csv"
MERGED_DAYS = OUT_DIR / "merged_signal_days.csv"

BEST_FULL = OUT_DIR / "company_daily_best_full_history.csv"
BEST_FROZEN = OUT_DIR / "company_daily_best_frozen.csv"
ALL_FULL = OUT_DIR / "company_daily_all_signals_full_history.csv"
ALL_FROZEN = OUT_DIR / "company_daily_all_signals_frozen.csv"
DETAIL_FULL = OUT_DIR / "company_signal_detail_full_history.csv"
DETAIL_FROZEN = OUT_DIR / "company_signal_detail_frozen.csv"
MAPPING = OUT_DIR / "company_strategy_mapping.csv"

def evaluate(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
    min_n: int = 100,
    min_p: float = 0.52,
    min_abs: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target.to_numpy(dtype=float))
    ev_dates = dates.to_numpy()[valid]
    vals = target.to_numpy(dtype=float)[valid] * 100.0
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool), np.array([], dtype="U11")
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
        dec_up = (cum_n >= min_n) & (p_up >= min_p) & (avg_up >= min_abs)
        dec_down = (cum_n >= min_n) & (p_down >= min_p) & (avg_down <= -min_abs)
    trade_mask = dec_up | dec_down
    decisions = np.where(dec_up, "predict_up", np.where(dec_down, "predict_down", "no_trade"))
    predicted = np.where(dec_up, avg_up, np.where(dec_down, avg_down, np.nan))
    return ev_dates, vals, trade_mask, predicted


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dual = pd.read_csv(DUAL, keep_default_na=False)
    summary = pd.read_csv(SUMMARY, keep_default_na=False)
    merged = pd.read_csv(MERGED_DAYS)
    merged["date"] = pd.to_datetime(merged["date"], format="%m/%d/%Y")

    master = build_master()
    masks = build_masks(master)
    fund_cols = set(pd.read_csv(OUT_DIR / "panel_fund_returns.csv").columns[1:])
    non_fund = {
        "Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp", "CreditSpread",
        "JNKSpread", "StkBonCorr", "USDGoldRatio", "SectRotation", "VIX_5dChg",
        "VIX_20dVol", "VIX_TNX_Ratio", "YldCurveProxy",
    }
    all_etfs = {c for c in master.columns if c not in fund_cols and c not in non_fund}
    dates = master["Date"]
    fund = wf.load_panel(OUT_DIR / "panel_fund_returns.csv")
    all_tickers = list(fund.columns[1:])
    dates_desc = fund["Date"].sort_values(ascending=False).tolist()

    # 1. Best signal per fund
    best_by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    detail_rows: list[dict] = []
    for _, row in summary.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        source = str(row["source"])
        if source == "main":
            params = (100, 0.55, 0.2)
        else:
            params = (100, 0.52, 0.15)
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        ev_dates, vals, trade_mask, predicted = evaluate(
            mask, get_target(master, ticker, horizon), dates, *params
        )
        if not trade_mask.any():
            continue
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        tp = predicted[trade_mask]
        best_by_fund[ticker] = {
            pd.Timestamp(d): float(v) for d, v in zip(td, tv)
        }
        for d, v, p in zip(td, tv, tp):
            detail_rows.append(
                {
                "ticker": ticker,
                "strategy": "best",
                "condition": condition,
                "horizon": horizon,
                "source": source,
                    "date": pd.Timestamp(d).strftime("%m/%d/%Y"),
                    "predicted_return": round(float(p), 6),
                    "actual_return": round(float(v), 6),
                }
            )

    # 2. All signals merged with R4 conflict rule
    all_by_fund: dict[str, dict[pd.Timestamp, float]] = {}
    operated = merged[merged["R4_strongest_direction"] != ""]
    for ticker, group in operated.groupby("ticker"):
        all_by_fund[ticker] = dict(zip(group["date"], group["actual"]))

    # 3. Write company-format tables (129 fund columns, uncovered stay blank)
    def full_map(mapping: dict[str, dict[pd.Timestamp, float]]) -> dict[str, dict[pd.Timestamp, float]]:
        return {t: mapping.get(t, {}) for t in all_tickers}

    write_daily_wide(BEST_FULL, dates_desc, all_tickers, full_map(best_by_fund))
    write_daily_wide(ALL_FULL, dates_desc, all_tickers, full_map(all_by_fund))

    frozen_dates = [d for d in dates_desc if d >= CUTOFF]

    def frozen_map(mapping: dict[str, dict[pd.Timestamp, float]]) -> dict[str, dict[pd.Timestamp, float]]:
        out = {}
        for ticker in all_tickers:
            out[ticker] = {
                d: v for d, v in mapping.get(ticker, {}).items() if d >= CUTOFF
            }
        return out

    write_daily_wide(BEST_FROZEN, frozen_dates, all_tickers, frozen_map(best_by_fund))
    write_daily_wide(ALL_FROZEN, frozen_dates, all_tickers, frozen_map(all_by_fund))

    # 4. Signal detail long tables
    detail = pd.DataFrame(detail_rows)
    detail_full = detail.sort_values(["ticker", "date"])
    detail_full.to_csv(DETAIL_FULL, index=False)
    detail_frozen = detail[
        pd.to_datetime(detail["date"], format="%m/%d/%Y") >= CUTOFF
    ].sort_values(["ticker", "date"])
    detail_frozen.to_csv(DETAIL_FROZEN, index=False)

    # 5. Strategy mapping
    mapping_rows = []
    for _, row in summary.iterrows():
        ticker = str(row["ticker"])
        mapping_rows.append(
            {
                "ticker": ticker,
                "fund_group": row["fund_group"],
                "best_condition": row["condition"],
                "best_horizon": int(row["horizon"]),
                "full_avg": row["full_avg"],
                "full_trades": row["full_trades"],
                "frozen_avg": row["frozen_avg"],
                "frozen_trades": row["frozen_trades"],
                "frozen_hit": row["frozen_hit"],
            }
        )
    mapping = pd.DataFrame(mapping_rows)
    mapping.to_csv(MAPPING, index=False)

    def stat_check(path: pathlib.Path) -> tuple[int, int]:
        df = pd.read_csv(path, skiprows=12)
        covered = 0
        ok = 0
        for col in df.columns[1:]:
            vals = df[col].dropna()
            if vals.empty:
                continue
            covered += 1
            if abs(vals.mean()) >= 0.2:
                ok += 1
        return covered, ok

    for path in [BEST_FULL, BEST_FROZEN, ALL_FULL, ALL_FROZEN]:
        covered, ok = stat_check(path)
        print(f"{path.name}: covered={covered}, avg>=0.2={ok}")

    print(f"best funds: {len(best_by_fund)}")
    print(f"all-R4 funds: {len(all_by_fund)}")
    print(f"detail rows: {len(detail)}")
    print(f"Saved: {BEST_FULL}, {BEST_FROZEN}, {ALL_FULL}, {ALL_FROZEN}")
    print(f"Saved: {DETAIL_FULL}, {DETAIL_FROZEN}, {MAPPING}")


if __name__ == "__main__":
    main()
