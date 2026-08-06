"""Recompute the full 76-ETF signal pool on the cleaned v4 master."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4


def load_cleaned_76_master() -> pd.DataFrame:
    panel = pd.read_csv(config.V4_ETF19_PANEL)
    if "date" in panel.columns:
        panel = panel.rename(columns={"date": "Date"})
    ext57 = pd.read_csv(config.PROCESSED / "combined_extended_etf_returns_adj.csv", skiprows=12)
    external = pd.read_csv(config.EXTERNAL_DAILY, parse_dates=["Date"])
    external = external[
        ["Date"]
        + [
            c
            for c in external.columns
            if c.startswith(("VIX", "TNX", "Credit", "JNK", "USD", "Sect", "Yld", "Stk"))
        ]
    ]
    for df in (panel, ext57):
        df["Date"] = pd.to_datetime(df["Date"])
    ext57_cols = [c for c in ext57.columns if c != "Date"]
    ext57[ext57_cols] = ext57[ext57_cols].clip(
        -config.ETF_RETURN_CLIP, config.ETF_RETURN_CLIP
    )
    master = (
        panel.merge(ext57, on="Date", how="left")
        .merge(external, on="Date", how="left")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return master


def load_pools() -> pd.DataFrame:
    v3 = pd.read_csv(config.V3_PASS, keep_default_na=False)
    pair = pd.read_csv(config.PAIR_STRICT, keep_default_na=False)
    candidates = pd.read_csv(config.V3_CANDIDATES_STATS, keep_default_na=False)
    cols = [
        "ticker",
        "fund_group",
        "source",
        "condition",
        "horizon",
        "full_avg",
        "full_trades",
        "full_hit",
        "frozen_avg",
        "frozen_trades",
        "frozen_hit",
    ]
    pool = pd.concat([v3[cols], pair[cols], candidates[cols]], ignore_index=True)
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    return pool.reset_index(drop=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)
    master = load_cleaned_76_master()
    fund_cols = set(pd.read_csv(config.FUND_PANEL).columns[1:])
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_cols and c not in non_fund}
    dates = master["Date"].to_numpy()
    pool = load_pools()
    print("pool rows:", len(pool), "funds", pool["ticker"].nunique(), "etfs", len(all_etfs), flush=True)

    mask_cache: dict[tuple[str, str | None], pd.Series] = {}
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    rows: list[dict] = []

    def get_mask(condition: str, ticker: str) -> pd.Series:
        key = (condition, ticker if condition.startswith("self_") else None)
        if key not in mask_cache:
            mask_cache[key] = s4.build_condition_mask(master, condition, ticker, all_etfs)
        return mask_cache[key]

    def get_target(ticker: str, horizon: int, strict: bool) -> np.ndarray:
        key = (ticker, horizon, strict)
        if key not in target_cache:
            target_cache[key] = s4.multi_day_target(master, ticker, horizon, strict)
        return target_cache[key]

    for i, row in enumerate(pool.itertuples(index=False), start=1):
        ticker = str(row.ticker)
        condition = str(row.condition)
        horizon = int(row.horizon)
        source = str(row.source)
        mask = get_mask(condition, ticker)
        target = get_target(ticker, horizon, strict=source == "pair_scan")
        ev_dates, vals, trade_mask = s4.evaluate(mask, target, dates, *s4.params_for(source))
        if not trade_mask.any():
            continue
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        hold = td >= np.datetime64("2025-01-01")
        rows.append(
            {
                "ticker": ticker,
                "fund_group": row.fund_group,
                "source": source,
                "condition": condition,
                "horizon": horizon,
                "full_avg": float(tv.mean()),
                "full_trades": int(tv.size),
                "full_hit": float((tv > 0).mean()),
                "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
                "frozen_trades": int(hold.sum()),
                "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
            }
        )
        if i % 10000 == 0:
            print(f"recomputed {i}/{len(pool)}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(config.V4_OUT / "v4_76pool_recomputed.csv", index=False)
    print("saved:", config.V4_OUT / "v4_76pool_recomputed.csv", "rows", len(out))


if __name__ == "__main__":
    main()
