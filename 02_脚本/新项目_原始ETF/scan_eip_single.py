# -*- coding: utf-8 -*-
"""Phase 2: single-condition scan (original 19 ETFs only, horizons 1/2/3).

Condition space: 19 ETF x {up, down, big_up, big_down, gt2, lt-2} x horizon {1,2,3}.
Execution caliber: T-day ETF signal -> T+1-day fund return (future N-day mean).
Reuses v4 walk-forward decision (evaluate_mask) and target builder (build_target).

Output: 04_结果/新项目_原始ETF/中间结果/eip_single_pass.csv
(all evaluated signals with full/frozen stats + pass flag under recommended thresholds)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config_eip as config


CUTOFF = np.datetime64(config.CUTOFF)


def build_target(fund_arr: np.ndarray, horizon: int) -> np.ndarray:
    """fund_arr is (n, f) decimal returns -> future N-day mean returns in percent."""
    n, f = fund_arr.shape
    if horizon == 1:
        out = np.full((n, f), np.nan)
        out[:-1, :] = fund_arr[1:, :]
        return out * 100.0
    shifted = np.empty((n, f, horizon))
    for k in range(1, horizon + 1):
        shifted[:, :, k - 1] = np.roll(fund_arr, -k, axis=0)
    shifted[-horizon:, :, :] = np.nan
    valid = ~np.isnan(shifted).any(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = shifted.mean(axis=2)
    return np.where(valid, mean * 100.0, np.nan)


def evaluate_mask(
    mask: np.ndarray,
    target_col: np.ndarray,
    dates: np.ndarray,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    valid = mask & np.isfinite(target_col)
    idx = np.flatnonzero(valid)
    ev_dates = dates[idx]
    vals = target_col[idx]
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool)
    up = vals > 0
    down = vals < 0
    cum_n = np.arange(n, dtype=float)
    cum_up = np.concatenate([[0.0], np.cumsum(up)[:-1]])
    cum_down = np.concatenate([[0.0], np.cumsum(down)[:-1]])
    cum_su = np.concatenate([[0.0], np.cumsum(np.where(up, vals, 0.0))[:-1]])
    cum_sd = np.concatenate([[0.0], np.cumsum(np.where(down, vals, 0.0))[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_up = cum_up / cum_n
        p_down = cum_down / cum_n
        avg_up = cum_su / np.where(cum_up > 0, cum_up, 1)
        avg_down = cum_sd / np.where(cum_down > 0, cum_down, 1)
        dec_up = (cum_n >= min_n) & (p_up >= min_p) & (avg_up >= min_abs)
        dec_down = (cum_n >= min_n) & (p_down >= min_p) & (avg_down <= -min_abs)
    trade_mask = dec_up | dec_down
    return ev_dates, vals, trade_mask


def build_etf_mask(master: pd.DataFrame, condition: str) -> np.ndarray:
    tokens = condition.split("_")
    etf = tokens[0]
    suffix = "_".join(tokens[1:])
    s = master[etf]
    if suffix == "up":
        return (s > 0).to_numpy(dtype=bool)
    if suffix == "down":
        return (s < 0).to_numpy(dtype=bool)
    if suffix == "big_up":
        return (s >= 1.0).to_numpy(dtype=bool)
    if suffix == "big_down":
        return (s <= -1.0).to_numpy(dtype=bool)
    if suffix == "gt2":
        return (s > 2.0).to_numpy(dtype=bool)
    if suffix == "lt-2":
        return (s < -2.0).to_numpy(dtype=bool)
    raise ValueError(f"cannot parse condition: {condition}")


def is_pass(row: dict) -> bool:
    return bool(
        abs(row["full_avg"]) >= config.MIN_ABS_AVG
        and row["full_trades"] >= config.RECOMMENDED_FULL_TRADES
        and row["full_hit"] > config.MIN_FULL_HIT
        and row["frozen_avg"] == row["frozen_avg"]
        and abs(row["frozen_avg"]) >= config.MIN_ABS_AVG
        and row["frozen_trades"] >= config.RECOMMENDED_FROZEN_TRADES
        and row["frozen_hit"] >= config.MIN_FROZEN_HIT
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.MIDDLE.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(config.PANEL_PATH)
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel = panel.sort_values("Date").reset_index(drop=True)
    fund_cols = [c for c in panel.columns if c not in {"Date"} | config.ORIGINAL19_SET]
    if not fund_cols:
        print("no fund columns in panel")
        sys.exit(1)
    print(f"panel rows: {len(panel)}  funds: {len(fund_cols)}")

    dates = panel["Date"].to_numpy()
    fund_arr = panel[fund_cols].to_numpy(dtype=float)
    targets = {h: build_target(fund_arr, h) for h in config.HORIZONS}

    conditions = [
        f"{etf}_{suffix}"
        for etf in sorted(config.ORIGINAL19)
        for suffix in ["up", "down", "big_up", "big_down", "gt2", "lt-2"]
    ]

    rows: list[dict] = []
    n_checked = 0
    for cond in conditions:
        mask = build_etf_mask(panel, cond)
        for horizon in config.HORIZONS:
            target = targets[horizon]
            for fi, ticker in enumerate(fund_cols):
                tcol = target[:, fi]
                valid = mask & np.isfinite(tcol)
                if int(valid.sum()) < config.RAW_EVENT_MIN:
                    continue
                if int((valid & (dates >= CUTOFF)).sum()) < config.RECOMMENDED_FROZEN_TRADES:
                    continue
                ev_dates, vals, trade_mask = evaluate_mask(
                    mask, tcol, dates,
                    config.DECISION_N, config.DECISION_P, config.DECISION_ABS,
                )
                if not trade_mask.any():
                    continue
                td = ev_dates[trade_mask]
                tv = vals[trade_mask]
                hold = td >= CUTOFF
                row = {
                    "ticker": ticker,
                    "condition": cond,
                    "horizon": horizon,
                    "source": "single_scan",
                    "full_avg": float(tv.mean()),
                    "full_trades": int(tv.size),
                    "full_hit": float((tv > 0).mean()),
                    "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
                    "frozen_trades": int(hold.sum()),
                    "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
                }
                row["pass"] = is_pass(row)
                rows.append(row)
            n_checked += 1
        if n_checked % 60 == 0:
            print(f"condition-horizons checked: {n_checked}  signals: {len(rows)}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(config.MIDDLE / "eip_single_pass.csv", index=False, encoding="utf-8-sig")
    print("checked condition-horizons:", n_checked)
    print("total evaluated signals:", len(out))
    if len(out):
        passed = out[out["pass"]]
        print("pass signals:", len(passed), " covered funds:", passed["ticker"].nunique())
        print("funds with any signal:", out["ticker"].nunique())
    print("saved:", config.MIDDLE / "eip_single_pass.csv")


if __name__ == "__main__":
    main()