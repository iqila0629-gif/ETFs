"""Regenerate dual-criteria formal outputs with frozen hit rate >= 55%."""

from __future__ import annotations

import pathlib
import shutil
import sys

import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_daily_tables import write_daily_wide
from generate_predictions import write_standard_csv
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
BACKUP = OUT_DIR / "dual_criteria_pass_hit45_backup.csv"
SUMMARY = OUT_DIR / "dual_criteria_summary.csv"
FULL_OUT = OUT_DIR / "final_outputs_dual_full_history"
FROZEN_OUT = OUT_DIR / "final_outputs_dual_frozen"

MIN_HIT = 0.55
MIN_N = 100
MIN_P = 0.52
MIN_ABS = 0.15


def evaluate(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Decisions are not needed here; return dates and values only."""
    import numpy as np

    valid = mask.to_numpy(dtype=bool) & target.notna().to_numpy(dtype=bool)
    ev_dates = dates.to_numpy()[valid]
    vals = target.to_numpy(dtype=float)[valid] * 100.0
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool)
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
    return ev_dates, vals, trade_mask


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not BACKUP.exists():
        shutil.copy2(DUAL, BACKUP)

    dual = pd.read_csv(DUAL, keep_default_na=False)
    for col in ["frozen_hit"]:
        dual[col] = pd.to_numeric(dual[col], errors="coerce")
    dual = dual[dual["frozen_hit"] >= MIN_HIT].copy()
    dual = dual.drop_duplicates(subset=["ticker", "condition", "horizon"], keep="first")
    dual.to_csv(DUAL, index=False)

    best_rows = []
    for ticker, group in dual.groupby("ticker"):
        row = group.reindex(group["full_avg"].abs().sort_values(ascending=False).index).iloc[0]
        best_rows.append(row)
    best = pd.DataFrame(best_rows).sort_values("ticker").reset_index(drop=True)
    best.to_csv(SUMMARY, index=False)

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

    for folder in (FULL_OUT, FROZEN_OUT):
        folder.mkdir(parents=True, exist_ok=True)
        for path in folder.glob("*.csv"):
            path.unlink()

    generated = 0
    for _, row in dual.iterrows():
        ticker = row["ticker"]
        condition = row["condition"]
        horizon = int(row["horizon"])
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        ev_dates, vals, trade_mask = evaluate(mask, get_target(master, ticker, horizon), dates)
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        if not td.size:
            continue
        full_rows = [
            (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
            for d, v in sorted(zip(td, tv), key=lambda x: x[0], reverse=True)
        ]
        hold = td >= CUTOFF
        frozen_rows = [
            (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
            for d, v in sorted(zip(td[hold], tv[hold]), key=lambda x: x[0], reverse=True)
        ]
        name = f"{ticker}__{condition}" + (f"__N{horizon}" if horizon > 1 else "")
        write_standard_csv(FULL_OUT / f"{name}.csv", full_rows)
        if frozen_rows:
            write_standard_csv(FROZEN_OUT / f"{name}.csv", frozen_rows)
            generated += 1

    print(f"dual pass at >=55%: {len(dual)} rows, {dual['ticker'].nunique()} funds")
    print(f"best-fund summary: {len(best)} rows")
    print(f"full/frozen CSVs generated: {generated}")


if __name__ == "__main__":
    main()
