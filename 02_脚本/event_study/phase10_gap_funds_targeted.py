"""Phase 10: targeted sweep for the six remaining low-volatility gap funds."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_predictions import write_standard_csv
from phase9_dual_criteria_pipeline import (
    CUTOFF,
    build_master,
    build_masks,
    get_target,
    is_dual_pass,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FIT_MATRIX = OUT_DIR / "fund_etf_fit_matrix.csv"
REPORT = OUT_DIR / "gap_funds_targeted_validation.csv"
FULL_OUT = OUT_DIR / "final_outputs_gap_targeted_full_history"
FROZEN_OUT = OUT_DIR / "final_outputs_gap_targeted_frozen"

TARGETS = ["FDPIX", "FDPSX", "RDPIX", "RDPSX", "RTPIX", "RTPSX"]
HORIZONS = [1, 2, 3, 5, 10]
MIN_N = 100
MIN_P = 0.50
MIN_ABS = 0.10


def evaluate(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
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
        dec_up = (cum_n >= MIN_N) & (p_up >= MIN_P) & (avg_up >= MIN_ABS)
        dec_down = (cum_n >= MIN_N) & (p_down >= MIN_P) & (avg_down <= -MIN_ABS)
    trade_mask = dec_up | dec_down
    decisions = np.where(dec_up, "predict_up", np.where(dec_down, "predict_down", "no_trade"))
    return ev_dates, vals, trade_mask, decisions


def combo_stats(mask: pd.Series, target: pd.Series, dates: pd.Series) -> dict:
    ev_dates, vals, trade_mask, decisions = evaluate(mask, target, dates)
    out = {
        "full_avg": float("nan"),
        "full_trades": 0,
        "frozen_avg": float("nan"),
        "frozen_trades": 0,
        "frozen_hit": float("nan"),
    }
    if not trade_mask.any():
        return out
    td = ev_dates[trade_mask]
    tv = vals[trade_mask]
    hd = decisions[trade_mask]
    out["full_avg"] = float(tv.mean())
    out["full_trades"] = int(tv.size)
    hold = td >= CUTOFF
    if hold.any():
        hv = tv[hold]
        out["frozen_avg"] = float(hv.mean())
        out["frozen_trades"] = int(hv.size)
        out["frozen_hit"] = float(
            (((hd[hold] == "predict_up") & (hv > 0)) | ((hd[hold] == "predict_down") & (hv < 0))).mean()
        )
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    FULL_OUT.mkdir(parents=True, exist_ok=True)
    FROZEN_OUT.mkdir(parents=True, exist_ok=True)
    master = build_master()
    masks = build_masks(master)
    dates = master["Date"]
    all_etfs = {
        c
        for c in masks
        if not c.startswith(("self_", "ext_"))
        and not c.startswith("SPY_")
        and not c.startswith("majority")
        and not c.startswith("all_")
        and "_bin_" in c
    }
    all_etfs = {c.split("_bin_")[0] for c in all_etfs}

    fit = pd.read_csv(FIT_MATRIX)
    rows: list[dict] = []
    generated = 0
    for ticker in TARGETS:
        fr = master[ticker]
        top = (
            fit[fit["Fund"] == ticker]
            .assign(corr=pd.to_numeric(fit[fit["Fund"] == ticker]["Same"], errors="coerce"))
            .sort_values("corr", ascending=False)
            .head(3)
        )
        top_etfs = top["ETF"].tolist()
        best_etf = top_etfs[0] if top_etfs else "SPY"

        conditions: list[tuple[str, pd.Series]] = []
        for etf in sorted(all_etfs):
            s = master[etf]
            for name in ["up", "down", "big_up", "big_down", "gt2", "lt-2"]:
                if name == "up":
                    mask = s > 0
                elif name == "down":
                    mask = s < 0
                elif name == "big_up":
                    mask = s >= 1.0
                elif name == "big_down":
                    mask = s <= -1.0
                elif name == "gt2":
                    mask = s > 2.0
                else:
                    mask = s < -2.0
                conditions.append((f"{etf}_{name}", mask))

        if len(top_etfs) >= 3:
            a, b, c = top_etfs[0], top_etfs[1], top_etfs[2]
            conditions.append((f"{a}_{b}_{c}_all_up", (master[a] > 0) & (master[b] > 0) & (master[c] > 0)))
            conditions.append((f"{a}_{b}_{c}_all_down", (master[a] < 0) & (master[b] < 0) & (master[c] < 0)))
        if len(top_etfs) >= 2:
            a, b = top_etfs[0], top_etfs[1]
            conditions.append((f"{a}_up_{b}_down", (master[a] > 0) & (master[b] < 0)))
            conditions.append((f"{a}_down_{b}_up", (master[a] < 0) & (master[b] > 0)))

        r = master[ticker]
        for name, mask in [
            ("self_up", r > 0),
            ("self_down", r < 0),
            ("self_big_up", r >= 0.01),
            ("self_big_down", r <= -0.01),
            ("self_3up", (r > 0) & (r.shift(1) > 0) & (r.shift(2) > 0)),
            ("self_3down", (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0)),
        ]:
            conditions.append((name, mask))

        vol20 = master[best_etf].rolling(20).std()
        base = vol20.shift(1).rolling(250).median()
        high = vol20 > base
        low = vol20 < base
        s = master[best_etf]
        conditions.extend(
            [
                (f"regime_high_up", high & (s > 0)),
                (f"regime_high_down", high & (s < 0)),
                (f"regime_low_up", low & (s > 0)),
                (f"regime_low_down", low & (s < 0)),
            ]
        )
        conditions.extend(
            [
                ("ext_credit_gt0", master["CreditSpread"] > 0),
                ("ext_credit_lt0", master["CreditSpread"] < 0),
                ("ext_jnk_gt0", master["JNKSpread"] > 0),
                ("ext_jnk_lt0", master["JNKSpread"] < 0),
            ]
        )

        for condition, mask in conditions:
            for horizon in HORIZONS:
                stats = combo_stats(mask, get_target(master, ticker, horizon), dates)
                dual = is_dual_pass(stats)
                loose = (
                    stats["full_avg"] == stats["full_avg"]
                    and abs(stats["full_avg"]) >= 0.2
                    and stats["full_trades"] >= 30
                    and stats["frozen_avg"] == stats["frozen_avg"]
                    and abs(stats["frozen_avg"]) >= 0.2
                    and stats["frozen_trades"] >= 10
                    and stats["frozen_hit"] == stats["frozen_hit"]
                    and stats["frozen_hit"] >= 0.45
                )
                rows.append(
                    {
                        "ticker": ticker,
                        "fund_group": em.fund_group(ticker),
                        "condition": condition,
                        "horizon": horizon,
                        **stats,
                        "dual_pass": dual,
                        "dual_pass_loose_trades": loose,
                    }
                )
                if dual:
                    ev_dates, vals, trade_mask, decisions = evaluate(mask, get_target(master, ticker, horizon), dates)
                    td = ev_dates[trade_mask]
                    tv = vals[trade_mask]
                    name = f"{ticker}__{condition}" + (f"__N{horizon}" if horizon > 1 else "")
                    full_rows = [
                        (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
                        for d, v in sorted(zip(td, tv), key=lambda x: x[0], reverse=True)
                    ]
                    hold = td >= CUTOFF
                    frozen_rows = [
                        (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
                        for d, v in sorted(zip(td[hold], tv[hold]), key=lambda x: x[0], reverse=True)
                    ]
                    write_standard_csv(FULL_OUT / f"{name}.csv", full_rows)
                    if frozen_rows:
                        write_standard_csv(FROZEN_OUT / f"{name}.csv", frozen_rows)
                        generated += 1
        print(f"done {ticker}", flush=True)

    report = pd.DataFrame(rows)
    report = report.sort_values("full_avg", key=lambda s: s.abs(), ascending=False)
    report.to_csv(REPORT, index=False)
    dual = report[report["dual_pass"]]
    loose = report[report["dual_pass_loose_trades"]]
    print(f"combos evaluated: {len(report)}")
    print(f"dual pass (full_trades>=50): {len(dual)}, funds: {dual['ticker'].nunique() if not dual.empty else 0}")
    print(f"dual pass (full_trades>=30): {len(loose)}, funds: {loose['ticker'].nunique() if not loose.empty else 0}")
    if not dual.empty:
        cols = ["ticker", "condition", "horizon", "full_avg", "full_trades", "frozen_avg", "frozen_trades", "frozen_hit"]
        print(dual[cols].head(20).to_string(index=False))
    if not loose.empty:
        cols = ["ticker", "condition", "horizon", "full_avg", "full_trades", "frozen_avg", "frozen_trades", "frozen_hit"]
        print("loose examples:")
        print(loose[cols].head(20).to_string(index=False))
    print(f"formal CSVs generated: {generated}")
    print(f"Saved: {REPORT}")


if __name__ == "__main__":
    main()
