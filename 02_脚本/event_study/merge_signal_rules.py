"""Evaluate same-day multi-signal merge rules for each fund."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import event_metrics as em
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
DAYS_OUT = OUT_DIR / "merged_signal_days.csv"
EVAL_OUT = OUT_DIR / "merged_rule_evaluation.csv"

MIN_N = 100
MIN_P = 0.52
MIN_ABS = 0.15


def evaluate_with_pred(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target.to_numpy(dtype=float))
    ev_dates = dates.to_numpy()[valid]
    vals = target.to_numpy(dtype=float)[valid] * 100.0
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


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master = build_master()
    masks = build_masks(master)
    fund_cols = set(master.columns) - set(
        pd.read_csv(OUT_DIR / "panel_fund_returns.csv").columns
    )
    fund_cols = set(pd.read_csv(OUT_DIR / "panel_fund_returns.csv").columns[1:])
    non_fund = {
        "Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp", "CreditSpread",
        "JNKSpread", "StkBonCorr", "USDGoldRatio", "SectRotation", "VIX_5dChg",
        "VIX_20dVol", "VIX_TNX_Ratio", "YldCurveProxy",
    }
    all_etfs = {c for c in master.columns if c not in fund_cols and c not in non_fund}
    dates = master["Date"]

    dual = pd.read_csv(DUAL, keep_default_na=False)
    dual = dual.drop_duplicates(subset=["ticker", "condition", "horizon"], keep="first")
    dual["strength"] = dual["full_avg"].abs()

    days: dict[tuple[str, pd.Timestamp], dict] = {}
    for _, row in dual.iterrows():
        ticker = row["ticker"]
        condition = row["condition"]
        horizon = int(row["horizon"])
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        ev_dates, vals, trade_mask, decisions, predicted = evaluate_with_pred(
            mask, get_target(master, ticker, horizon), dates
        )
        if not trade_mask.any():
            continue
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        td_dec = decisions[trade_mask]
        td_pred = predicted[trade_mask]
        for i in range(td.size):
            d = pd.Timestamp(td[i])
            key = (ticker, d)
            rec = days.setdefault(
                key,
                {
                    "ticker": ticker,
                    "date": d,
                    "actual": float(tv[i]),
                    "n_up": 0,
                    "n_down": 0,
                    "pred_up": [],
                    "pred_down": [],
                    "strength_up": 0.0,
                    "strength_down": 0.0,
                    "strongest_dir": "",
                    "strongest_pred": float("nan"),
                },
            )
            if td_dec[i] == "predict_up":
                rec["n_up"] += 1
                rec["pred_up"].append(float(td_pred[i]))
                rec["strength_up"] = max(rec["strength_up"], float(row["strength"]))
            else:
                rec["n_down"] += 1
                rec["pred_down"].append(float(td_pred[i]))
                rec["strength_down"] = max(rec["strength_down"], float(row["strength"]))
            if row["strength"] > max(rec["strength_up"], rec["strength_down"]) or (
                rec["strongest_dir"] == ""
            ):
                rec["strongest_dir"] = "up" if td_dec[i] == "predict_up" else "down"
                rec["strongest_pred"] = float(td_pred[i])

    day_rows = []
    for (ticker, d), rec in days.items():
        n_up = rec["n_up"]
        n_down = rec["n_down"]
        conflict = n_up > 0 and n_down > 0
        actual = rec["actual"]

        def direction_for(rule: str) -> str:
            if rule == "R4_strongest":
                return rec["strongest_dir"]
            if rule == "R1_always":
                if n_up == n_down:
                    return rec["strongest_dir"]
                return "up" if n_up > n_down else "down"
            if rule == "R2_no_conflict":
                return "" if conflict else ("up" if n_up > 0 else "down")
            if rule == "R3_majority":
                if n_up == n_down:
                    return ""
                return "up" if n_up > n_down else "down"
            return ""

        def predicted_for(rule: str, direction: str) -> float:
            if direction == "":
                return float("nan")
            if rule == "R4_strongest":
                return rec["strongest_pred"]
            if rule == "R1_always":
                if n_up == n_down:
                    return rec["strongest_pred"]
                pool = rec["pred_up"] if direction == "up" else rec["pred_down"]
                return float(np.mean(pool)) if pool else rec["strongest_pred"]
            pool = rec["pred_up"] if direction == "up" else rec["pred_down"]
            return float(np.mean(pool)) if pool else float("nan")

        row = {
            "ticker": ticker,
            "date": d.strftime("%m/%d/%Y"),
            "actual": actual,
            "n_signals": n_up + n_down,
            "n_up": n_up,
            "n_down": n_down,
            "conflict": conflict,
            "strongest_dir": rec["strongest_dir"],
            "strongest_pred": round(rec["strongest_pred"], 4),
        }
        for rule in ["R1_always", "R2_no_conflict", "R3_majority", "R4_strongest"]:
            direction = direction_for(rule)
            row[f"{rule}_direction"] = direction
            row[f"{rule}_predicted"] = round(predicted_for(rule, direction), 4)
            row[f"{rule}_hit"] = (
                (direction == "up" and actual > 0) or (direction == "down" and actual < 0)
                if direction
                else ""
            )
        day_rows.append(row)
    day_df = pd.DataFrame(day_rows).sort_values(["ticker", "date"])
    day_df.to_csv(DAYS_OUT, index=False)

    eval_rows = []
    for rule in ["R1_always", "R2_no_conflict", "R3_majority", "R4_strongest"]:
        for ticker, group in day_df.groupby("ticker"):
            operated = group[group[f"{rule}_direction"] != ""]
            if operated.empty:
                continue
            actuals = operated["actual"]
            full_avg = float(actuals.mean())
            full_trades = int(len(actuals))
            hold = pd.to_datetime(operated["date"], format="%m/%d/%Y") >= pd.Timestamp("2025-01-01")
            hv = actuals[hold]
            frozen_avg = float(hv.mean()) if hv.size else float("nan")
            frozen_trades = int(hv.size)
            hits = operated[f"{rule}_hit"]
            frozen_hit = (
                float((hits[hold].astype(float) == 1).mean()) if hv.size else float("nan")
            )
            dual_pass = (
                abs(full_avg) >= 0.2
                and full_trades >= 50
                and frozen_avg == frozen_avg
                and abs(frozen_avg) >= 0.2
                and frozen_trades >= 10
                and frozen_hit == frozen_hit
                and frozen_hit >= 0.45
            )
            eval_rows.append(
                {
                    "ticker": ticker,
                    "fund_group": em.fund_group(ticker),
                    "rule": rule,
                    "trigger_days": int(len(group)),
                    "operated_days": full_trades,
                    "skipped_days": int(len(group) - len(operated)),
                    "full_avg": round(full_avg, 4),
                    "frozen_avg": round(frozen_avg, 4) if frozen_avg == frozen_avg else "",
                    "frozen_trades": frozen_trades,
                    "frozen_hit": round(frozen_hit, 4) if frozen_hit == frozen_hit else "",
                    "dual_pass": dual_pass,
                }
            )
    eval_df = pd.DataFrame(eval_rows)
    eval_df.to_csv(EVAL_OUT, index=False)

    total_days = len(day_df)
    conflict_days = int(day_df["conflict"].sum())
    print(f"trigger days (dedup): {total_days}")
    print(f"conflict days: {conflict_days} ({conflict_days / total_days * 100:.2f}%)" if total_days else "no days")
    for rule in ["R1_always", "R2_no_conflict", "R3_majority", "R4_strongest"]:
        sub = eval_df[eval_df["rule"] == rule]
        print(f"{rule}: funds pass = {sub['dual_pass'].sum()} / {len(sub)}")
    print(f"Saved: {DAYS_OUT}")
    print(f"Saved: {EVAL_OUT}")


if __name__ == "__main__":
    main()
