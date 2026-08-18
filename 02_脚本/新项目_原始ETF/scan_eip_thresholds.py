# -*- coding: utf-8 -*-
"""Phase 3: compliance screening + threshold sensitivity on the single-condition pool.

Dual caliber: full history + frozen period (2025-01-01+). Thresholds start identical
to v4 (full trades >=120, frozen >=30, |Average| >=0.2%, hit >=55%) and are swept over
full x {50,80,100,120} x frozen x {10,15,20,30} to produce a coverage report.

Outputs (04_结果/新项目_原始ETF/中间结果/):
  eip_threshold_sensitivity.csv
  eip_single_baseline_pass.csv   (recommended thresholds)
  eip_single_best_strategy.csv   (best per fund, recommended thresholds)
  eip_uncovered.csv              (clean targets with no strategy at recommended thresholds)
"""
from __future__ import annotations

import sys

import pandas as pd

import config_eip as config


def pass_flags(df: pd.DataFrame, full_min: int, frozen_min: int) -> pd.Series:
    return (
        df["full_avg"].abs().ge(config.MIN_ABS_AVG)
        & df["full_trades"].ge(full_min)
        & df["full_hit"].gt(config.MIN_FULL_HIT)
        & df["frozen_avg"].abs().ge(config.MIN_ABS_AVG)
        & df["frozen_trades"].ge(frozen_min)
        & df["frozen_hit"].ge(config.MIN_FROZEN_HIT)
    )


def best_per_fund(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["abs_full_avg"] = df["full_avg"].abs()
    return (
        df.sort_values(
            ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=False,
        )
        .groupby("ticker", sort=True)
        .head(1)
        .sort_values("ticker")
        .reset_index(drop=True)
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.MIDDLE.mkdir(parents=True, exist_ok=True)

    pool = pd.read_csv(config.MIDDLE / "eip_single_pass.csv", encoding="utf-8-sig")
    targets = config.load_clean_targets()
    all_targets = set(targets["name"])
    print("pool signals:", len(pool), " funds with any signal:", pool["ticker"].nunique())
    print("clean targets:", len(all_targets))

    sensitivity_rows: list[dict] = []
    for full_min in config.THRESHOLD_GRID_FULL:
        for frozen_min in config.THRESHOLD_GRID_FROZEN:
            ok = pool[pass_flags(pool, full_min, frozen_min)]
            best = best_per_fund(ok)
            covered = set(best["ticker"])
            uncovered = sorted(all_targets - covered)
            row = {
                "full_min_trades": full_min,
                "frozen_min_trades": frozen_min,
                "signals": len(ok),
                "covered_funds": len(covered),
                "uncovered_count": len(uncovered),
                "uncovered_list": "|".join(uncovered),
            }
            if len(best):
                row.update({
                    "median_full_avg_abs": float(best["full_avg"].abs().median()),
                    "median_full_hit": float(best["full_hit"].median()),
                    "median_full_trades": int(best["full_trades"].median()),
                    "median_frozen_avg_abs": float(best["frozen_avg"].abs().median()),
                    "median_frozen_hit": float(best["frozen_hit"].median()),
                    "median_frozen_trades": int(best["frozen_trades"].median()),
                })
            else:
                row.update({
                    "median_full_avg_abs": "", "median_full_hit": "",
                    "median_full_trades": "", "median_frozen_avg_abs": "",
                    "median_frozen_hit": "", "median_frozen_trades": "",
                })
            sensitivity_rows.append(row)
            print(
                f"full>={full_min} frozen>={frozen_min}: signals={len(ok)} covered={len(covered)}",
                flush=True,
            )

    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(config.MIDDLE / "eip_threshold_sensitivity.csv", index=False, encoding="utf-8-sig")

    rec_full = config.RECOMMENDED_FULL_TRADES
    rec_frozen = config.RECOMMENDED_FROZEN_TRADES
    rec_ok = pool[pass_flags(pool, rec_full, rec_frozen)].copy()
    rec_ok["abs_full_avg"] = rec_ok["full_avg"].abs()
    rec_ok = rec_ok.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"], ascending=False
    )
    rec_ok.to_csv(config.MIDDLE / "eip_single_baseline_pass.csv", index=False, encoding="utf-8-sig")

    best_rec = best_per_fund(rec_ok)
    best_rec.to_csv(config.MIDDLE / "eip_single_best_strategy.csv", index=False, encoding="utf-8-sig")

    covered = set(best_rec["ticker"]) if len(best_rec) else set()
    uncovered = sorted(all_targets - covered)
    if uncovered:
        uv = targets[targets["name"].isin(uncovered)][["name", "category", "symbol", "overlap", "rows_ok"]]
        uv.to_csv(config.MIDDLE / "eip_uncovered.csv", index=False, encoding="utf-8-sig")
        print("uncovered funds:", len(uncovered), "->", config.MIDDLE / "eip_uncovered.csv")
    else:
        print("no uncovered funds")

    print(f"recommended {rec_full}/{rec_frozen}: signals={len(rec_ok)} funds={len(covered)}")
    print("saved sensitivity / baseline / best-strategy")


if __name__ == "__main__":
    main()