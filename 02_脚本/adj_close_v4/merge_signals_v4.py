"""Merge weak per-fund signals into OR/AND strategies to lift coverage."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4


CUTOFF = np.datetime64("2025-01-01")
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
MIN_ABS_AVG = 0.2
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55
MIN_CAND_FULL = 20
MIN_CAND_FROZEN = 5
K_RANGE = [2, 3, 4, 5]


def pass_stats(full_avg: float, full_trades: int, full_hit: float,
               frozen_avg: float, frozen_trades: int, frozen_hit: float) -> bool:
    return bool(
        abs(full_avg) >= MIN_ABS_AVG
        and full_trades >= FULL_MIN
        and full_hit > MIN_FULL_HIT
        and frozen_avg == frozen_avg
        and abs(frozen_avg) >= MIN_ABS_AVG
        and frozen_trades >= FROZEN_MIN
        and frozen_hit >= MIN_FROZEN_HIT
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    fund_set = set(fund_cols)
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    dates = master["Date"].to_numpy()

    best_path = config.V4_OUT / "v4_allmethods_best_strategy.csv"
    if not best_path.exists():
        best_path = config.V4_OUT / "v4_phase3_best_strategy.csv"
    best = pd.read_csv(best_path, keep_default_na=False)
    covered = set(best["ticker"])
    uncovered = [t for t in fund_cols if t not in covered and t not in config.MONEY_FUNDS]
    print("uncovered funds:", len(uncovered), flush=True)

    pool = pd.read_csv(config.V4_OUT / "v4_76pool_recomputed.csv", keep_default_na=False)
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    pool = pool[pool["ticker"].isin(uncovered)]
    all_known_tokens = {
        t
        for c in pool["condition"]
        for t in str(c).split("_")
        if t.isupper() and len(t) in (3, 4)
    }
    pool["etf_tokens"] = pool["condition"].apply(
        lambda c: {t for t in str(c).split("_") if t in all_known_tokens}
    )
    pool = pool[pool["etf_tokens"].apply(lambda s: s <= config.ORIGINAL19)]
    pool = pool[
        pool["full_trades"].ge(MIN_CAND_FULL) & pool["frozen_trades"].ge(MIN_CAND_FROZEN)
    ]
    print("eligible candidate rows:", len(pool), "funds", pool["ticker"].nunique(), flush=True)

    mask_cache: dict[tuple[str, str | None], pd.Series] = {}
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}

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

    fund_cands: dict[str, list[dict]] = {}
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
        rec = {
            "condition": condition,
            "horizon": horizon,
            "source": source,
            "strength": abs(float(row.full_avg)),
            "sign": 1 if float(row.full_avg) >= 0 else -1,
            "dates": set(pd.to_datetime(td)),
            "returns": dict(zip(pd.to_datetime(td), tv)),
        }
        fund_cands.setdefault(ticker, []).append(rec)
        if i % 1000 == 0:
            print(f"candidates built {i}/{len(pool)}", flush=True)

    def merged_stats(fund: str, cands: list[dict], mode: str) -> dict | None:
        if mode == "or":
            dates = set()
            for c in cands:
                dates |= c["dates"]
        else:
            dates = set(cands[0]["dates"])
            for c in cands[1:]:
                dates &= c["dates"]
        if not dates:
            return None
        by_date = {}
        for c in cands:
            for d in c["dates"]:
                if d in dates:
                    cur = by_date.get(d)
                    if cur is None or c["strength"] > cur[1]:
                        by_date[d] = (c["sign"], c["strength"], c["returns"][d])
        ordered = sorted(dates)
        tv = np.array([by_date[d][2] for d in ordered], dtype=float)
        td = np.array(ordered, dtype="datetime64[ns]")
        hold = td >= CUTOFF
        stats = {
            "full_avg": float(tv.mean()),
            "full_trades": int(tv.size),
            "full_hit": float((tv > 0).mean()),
            "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
            "frozen_trades": int(hold.sum()),
            "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
        }
        return stats

    pass_rows = []
    for ticker in uncovered:
        cands = fund_cands.get(ticker, [])
        if not cands:
            continue
        cands_sorted_strength = sorted(cands, key=lambda c: (-c["strength"], c["condition"]))
        cands_sorted_trades = sorted(cands, key=lambda c: (-len(c["dates"]), c["condition"]))
        found = False
        for ordering_name, ordering in [("strength", cands_sorted_strength), ("trades", cands_sorted_trades)]:
            if found:
                break
            for k in K_RANGE:
                if k > len(ordering):
                    continue
                selected = ordering[:k]
                for mode in ["or", "and"]:
                    stats = merged_stats(ticker, selected, mode)
                    if stats is None:
                        continue
                    if pass_stats(stats["full_avg"], stats["full_trades"], stats["full_hit"],
                                  stats["frozen_avg"], stats["frozen_trades"], stats["frozen_hit"]):
                        pass_rows.append(
                            {
                                "ticker": ticker,
                                "merge_mode": mode,
                                "ordering": ordering_name,
                                "k": k,
                                "conditions": "|".join(c["condition"] for c in selected),
                                "horizons": "|".join(str(c["horizon"]) for c in selected),
                                "full_avg": stats["full_avg"],
                                "full_trades": stats["full_trades"],
                                "full_hit": stats["full_hit"],
                                "frozen_avg": stats["frozen_avg"],
                                "frozen_trades": stats["frozen_trades"],
                                "frozen_hit": stats["frozen_hit"],
                            }
                        )
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if found:
            print("merged cover:", ticker, flush=True)

    out = pd.DataFrame(pass_rows)
    out.to_csv(config.V4_OUT / "v4_merged_strategies.csv", index=False)
    print("merged pass rows:", len(out), "funds", out["ticker"].nunique() if len(out) else 0)


if __name__ == "__main__":
    main()
