"""Combine single/double, triple, and condition-expansion passes into final pool."""

from __future__ import annotations

import sys

import pandas as pd

import config


MIN_ABS_AVG = 0.2
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    pool = pd.read_csv(config.V4_76POOL, keep_default_na=False)
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    all_tokens = {
        t
        for c in pool["condition"]
        for t in str(c).split("_")
        if t.isupper() and len(t) in (3, 4)
    }
    pool["tokens"] = pool["condition"].apply(
        lambda c: {t for t in str(c).split("_") if t in all_tokens}
    )
    ok = (
        pool["full_avg"].abs().ge(MIN_ABS_AVG)
        & pool["full_trades"].ge(FULL_MIN)
        & pool["full_hit"].gt(MIN_FULL_HIT)
        & pool["frozen_avg"].abs().ge(MIN_ABS_AVG)
        & pool["frozen_trades"].ge(FROZEN_MIN)
        & pool["frozen_hit"].ge(MIN_FROZEN_HIT)
    )
    base20 = pool[ok & pool["tokens"].apply(lambda t: t <= config.V4_UNIVERSE)].copy()
    base20.to_csv(config.V4_OUT / "v4_final20_v2_base_pass.csv", index=False)

    triple = pd.read_csv(config.V4_TRIPLE_PASS, keep_default_na=False)
    cond = pd.read_csv(config.V4_OUT / "v4_condition_expansion_pass.csv", keep_default_na=False)
    for df in (triple, cond):
        for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    combined = pd.concat([base20, triple, cond], ignore_index=True)
    combined["abs_full_avg"] = combined["full_avg"].abs()
    combined = combined.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
        ascending=False,
    ).drop_duplicates(["ticker", "condition", "horizon"], keep="first").reset_index(drop=True)
    combined.to_csv(config.V4_FINAL20_COMBINED_PASS, index=False)

    best = (
        combined.sort_values(
            ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=False,
        )
        .groupby("ticker", sort=True)
        .head(1)
        .sort_values("ticker")
        .reset_index(drop=True)
    )
    best.to_csv(config.V4_FINAL20_BEST, index=False)
    print("base20:", len(base20), "final pool:", len(combined), "funds:", combined["ticker"].nunique())


if __name__ == "__main__":
    main()
