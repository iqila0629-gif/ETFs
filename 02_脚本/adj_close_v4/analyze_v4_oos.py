"""v4 robustness analysis: out-of-sample fixed split + train-reselected validation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4
import select_v4_strategies as sel

TRAIN_END = np.datetime64("2024-12-31")
VAL_START = np.datetime64("2023-01-01")
TEST_START = np.datetime64("2025-01-01")
MIN_STRATEGIES = 3
MAX_STRATEGIES = 5
DENSITY_TIERS = [(200, 40), (160, 35), (120, 30)]
AVG_FLOOR = 0.30
OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def metric_dict(tv: np.ndarray) -> dict:
    n = int(tv.size)
    if n == 0:
        return {
            "trades": 0,
            "avg": float("nan"),
            "hit": float("nan"),
            "std": float("nan"),
            "ann_vol": float("nan"),
            "downside_std": float("nan"),
            "avg_std": float("nan"),
            "median": float("nan"),
            "p10": float("nan"),
            "p90": float("nan"),
            "max": float("nan"),
            "min": float("nan"),
            "tstat": float("nan"),
        }
    std = float(tv.std(ddof=1))
    avg = float(tv.mean())
    downside = float(np.sqrt(np.mean(np.minimum(tv, 0.0) ** 2)))
    return {
        "trades": n,
        "avg": avg,
        "hit": float((tv > 0).mean()),
        "std": std,
        "ann_vol": std * np.sqrt(252.0),
        "downside_std": downside,
        "avg_std": avg / std if std > 0 else float("nan"),
        "median": float(np.median(tv)),
        "p10": float(np.percentile(tv, 10)),
        "p90": float(np.percentile(tv, 90)),
        "max": float(tv.max()),
        "min": float(tv.min()),
        "tstat": avg / (std / np.sqrt(n)) if std > 0 else float("nan"),
    }


def merged_returns(selected: list[dict]) -> dict[np.datetime64, float]:
    by_date: dict[np.datetime64, tuple[float, float]] = {}
    for s in selected:
        for d, v in s["returns_full"].items():
            cur = by_date.get(d)
            if cur is None or s["strength"] > cur[1]:
                by_date[d] = (v, s["strength"])
    return {d: pair[0] for d, pair in by_date.items()}


def merged_test_returns(selected: list[dict]) -> dict[np.datetime64, float]:
    by_date: dict[np.datetime64, tuple[float, float]] = {}
    for s in selected:
        for d, v in s["returns_test"].items():
            cur = by_date.get(d)
            if cur is None or s["strength"] > cur[1]:
                by_date[d] = (v, s["strength"])
    return {d: pair[0] for d, pair in by_date.items()}


def returns_to_array(returns: dict[np.datetime64, float], keep) -> np.ndarray:
    return np.array(
        [v for d, v in sorted(returns.items()) if keep(d)],
        dtype=float,
    )


def evaluate_full(master, ticker, condition, horizon, source, all_etfs, target_cache):
    strict = source in ("pair_scan", "triple_scan", "condition_expansion")
    key = (ticker, horizon, strict)
    if key not in target_cache:
        target_cache[key] = s4.multi_day_target(master, ticker, horizon, strict)
    mask = sel.build_unified_mask(master, condition, ticker, all_etfs)
    target = target_cache[key]
    dates = master["Date"].to_numpy()
    ev_dates, vals, trade_mask = s4.evaluate(mask, target, dates, *s4.params_for(source))
    return ev_dates[trade_mask], vals[trade_mask]


def strategy_rec(master, ticker, condition, horizon, source, all_etfs, target_cache):
    strict = source in ("pair_scan", "triple_scan", "condition_expansion")
    key = (ticker, horizon, strict)
    if key not in target_cache:
        target_cache[key] = s4.multi_day_target(master, ticker, horizon, strict)
    mask = sel.build_unified_mask(master, condition, ticker, all_etfs)
    target = target_cache[key]
    dates = master["Date"].to_numpy()
    train_mask = dates < TRAIN_END
    train_ev, train_vals, train_trade = s4.evaluate(
        pd.Series(mask.to_numpy() & train_mask, index=master.index),
        target,
        dates,
        *s4.params_for(source),
    )
    td_tr = train_ev[train_trade]
    tv_tr = train_vals[train_trade]
    val_keep = (td_tr >= VAL_START) & (td_tr < TRAIN_END)
    td_val = td_tr[val_keep]
    tv_val = tv_tr[val_keep]
    test_keep = mask.to_numpy() & np.isfinite(target) & (dates >= TEST_START)
    td_te = dates[test_keep]
    tv_te = target[test_keep] * 100.0
    full = metric_dict(tv_tr)
    val = metric_dict(tv_val)
    test = metric_dict(tv_te)
    return {
        "condition": condition,
        "horizon": horizon,
        "source": source,
        "strength": abs(float(np.nanmean(tv_tr))) if tv_tr.size else 0.0,
        "train_avg": full["avg"],
        "train_trades": full["trades"],
        "train_hit": full["hit"],
        "train_std": full["std"],
        "full_trades": full["trades"],
        "full_avg": full["avg"],
        "full_hit": full["hit"],
        "val_avg": val["avg"],
        "val_trades": val["trades"],
        "val_hit": val["hit"],
        "test_avg": test["avg"],
        "test_trades": test["trades"],
        "test_hit": test["hit"],
        "test_std": test["std"],
        "returns_full": dict(zip(td_tr, tv_tr)),
        "returns_test": dict(zip(td_te, tv_te)),
        "dates": set(td_tr),
        "returns": dict(zip(td_tr, tv_tr)),
    }


def merge_stats_oos(selected: list[dict], start, end=None):
    tv = returns_to_array(merged_returns(selected), lambda d: d >= start and (end is None or d < end))
    return metric_dict(tv)


def constraints_ok_oos(merged: dict, baseline: dict, baseline_val: dict, dfull: int, dfrozen: int) -> bool:
    return bool(
        abs(merged["avg"]) >= max(0.9 * abs(baseline["avg"]), 0.2)
        and merged["hit"] >= baseline["hit"] - 0.03
        and merged["trades"] >= dfull
        and abs(merged["val_avg"]) >= max(0.9 * abs(baseline_val["avg"]), 0.2)
        and merged["val_hit"] >= baseline_val["hit"] - 0.03
        and merged["val_trades"] >= dfrozen
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    fund_set = set(fund_cols)
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    dates = master["Date"].to_numpy()

    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv", keep_default_na=False)

    if mode in ("fixed", "all"):
        target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
        rows = []
        merged_rows = []
        for r in mapping.itertuples(index=False):
            ticker = str(r.ticker)
            ev, tv = evaluate_full(master, ticker, str(r.condition), int(r.horizon), str(r.source), all_etfs, target_cache)
            tr_keep = ev < TRAIN_END
            te_keep = ev >= TEST_START
            rows.append({
                "ticker": ticker,
                "strategy_no": int(r.strategy_no),
                "source": r.source,
                "condition": r.condition,
                "horizon": int(r.horizon),
                **{f"full_{k}": v for k, v in metric_dict(tv).items()},
                **{f"train_{k}": v for k, v in metric_dict(tv[tr_keep]).items()},
                **{f"test_{k}": v for k, v in metric_dict(tv[te_keep]).items()},
            })
        pd.DataFrame(rows).to_csv(OUT_DIR / "v4_oos_fixed_split_by_strategy.csv", index=False)

        for ticker, group in mapping.groupby("ticker", sort=True):
            selected = []
            for r in group.itertuples(index=False):
                ev, tv = evaluate_full(master, ticker, str(r.condition), int(r.horizon), str(r.source), all_etfs, target_cache)
                selected.append({
                    "condition": str(r.condition),
                    "horizon": int(r.horizon),
                    "strength": abs(float(np.mean(tv))) if tv.size else 0.0,
                    "returns_full": dict(zip(ev, tv)),
                })
            merged_full = metric_dict(returns_to_array(merged_returns(selected), lambda d: True))
            merged_train = metric_dict(returns_to_array(merged_returns(selected), lambda d: d < TRAIN_END))
            merged_test = metric_dict(returns_to_array(merged_returns(selected), lambda d: d >= TEST_START))
            merged_rows.append({
                "ticker": ticker,
                "n_strategies": len(selected),
                **{f"full_{k}": v for k, v in merged_full.items()},
                **{f"train_{k}": v for k, v in merged_train.items()},
                **{f"test_{k}": v for k, v in merged_test.items()},
            })
        pd.DataFrame(merged_rows).to_csv(OUT_DIR / "v4_oos_fixed_split_merged.csv", index=False)
        print("fixed split done:", len(rows), "strategies,", len(merged_rows), "funds")

    if mode in ("reselect", "all"):
        pool = pd.read_csv(config.V4_FINAL20_COMBINED_PASS, keep_default_na=False)
        pool = pool[["ticker", "fund_group", "source", "condition", "horizon"]].drop_duplicates(
            ["ticker", "condition", "horizon"], keep="first"
        )
        print("pool rows:", len(pool), flush=True)
        target_cache = {}
        reselect_rows = []
        oos_rows = []
        for ticker, group in pool.groupby("ticker", sort=True):
            cands = []
            for r in group.itertuples(index=False):
                rec = strategy_rec(master, ticker, str(r.condition), int(r.horizon), str(r.source), all_etfs, target_cache)
                cands.append(rec)
            if not cands:
                continue
            baseline = merge_stats_oos(cands, dates[0], TRAIN_END)
            baseline_val = merge_stats_oos(cands, VAL_START, TRAIN_END)
            selected = None
            selected_stats = None
            density_tier = None
            for dfull, dfrozen in DENSITY_TIERS:
                cands_tier = [
                    c for c in cands
                    if c["train_trades"] >= dfull and c["val_trades"] >= dfrozen
                ]
                if not cands_tier:
                    continue
                sequence = sel.greedy_complement_sequence(cands_tier, AVG_FLOOR)
                best_found = None
                for k in range(MIN_STRATEGIES, min(len(sequence), MAX_STRATEGIES) + 1):
                    trial = sequence[:k]
                    merged = merge_stats_oos(trial, dates[0], TRAIN_END)
                    merged_val = merge_stats_oos(trial, VAL_START, TRAIN_END)
                    merged["val_avg"] = merged_val["avg"]
                    merged["val_trades"] = merged_val["trades"]
                    merged["val_hit"] = merged_val["hit"]
                    if constraints_ok_oos(merged, baseline, baseline_val, dfull, dfrozen):
                        best_found = (trial, merged)
                        break
                if best_found is not None:
                    selected, selected_stats = best_found
                    density_tier = (dfull, dfrozen)
                    break
            if selected is None:
                if cands:
                    selected = [max(cands, key=lambda s: s["strength"] * np.sqrt(s["train_trades"]))]
                    selected_stats = merge_stats_oos(selected, dates[0], TRAIN_END)
                density_tier = (120, 30)
            if selected is None:
                continue
            for idx, s in enumerate(selected, start=1):
                reselect_rows.append({
                    "ticker": ticker,
                    "strategy_no": idx,
                    "source": s["source"],
                    "condition": s["condition"],
                    "horizon": s["horizon"],
                    "train_avg": s["train_avg"],
                    "train_trades": s["train_trades"],
                    "train_hit": s["train_hit"],
                    "train_std": s["train_std"],
                    "val_avg": s["val_avg"],
                    "val_trades": s["val_trades"],
                    "val_hit": s["val_hit"],
                    "test_avg": s["test_avg"],
                    "test_trades": s["test_trades"],
                    "test_hit": s["test_hit"],
                    "test_std": s["test_std"],
                })
            test_merged = metric_dict(returns_to_array(merged_test_returns(selected), lambda d: True))
            train_merged = metric_dict(returns_to_array(merged_returns(selected), lambda d: d < TRAIN_END))
            oos_rows.append({
                "ticker": ticker,
                "n_strategies": len(selected),
                "density_full": density_tier[0],
                "density_frozen": density_tier[1],
                **{f"train_{k}": v for k, v in train_merged.items()},
                **{f"test_{k}": v for k, v in test_merged.items()},
            })
            if len(oos_rows) % 20 == 0:
                print(f"reselect {len(oos_rows)} funds", flush=True)
        pd.DataFrame(reselect_rows).to_csv(OUT_DIR / "v4_oos_reselected_strategies.csv", index=False)
        pd.DataFrame(oos_rows).to_csv(OUT_DIR / "v4_oos_reselected_merged.csv", index=False)
        print("reselect done:", len(oos_rows), "funds")

    if mode == "merged":
        reselected = pd.read_csv(OUT_DIR / "v4_oos_reselected_strategies.csv", keep_default_na=False)
        target_cache = {}
        oos_rows = []
        for ticker, group in reselected.groupby("ticker", sort=True):
            selected = []
            for r in group.itertuples(index=False):
                rec = strategy_rec(master, ticker, str(r.condition), int(r.horizon), str(r.source), all_etfs, target_cache)
                selected.append(rec)
            test_merged = metric_dict(returns_to_array(merged_test_returns(selected), lambda d: True))
            train_merged = metric_dict(returns_to_array(merged_returns(selected), lambda d: d < TRAIN_END))
            oos_rows.append({
                "ticker": ticker,
                "n_strategies": len(selected),
                "density_full": "",
                "density_frozen": "",
                **{f"train_{k}": v for k, v in train_merged.items()},
                **{f"test_{k}": v for k, v in test_merged.items()},
            })
        pd.DataFrame(oos_rows).to_csv(OUT_DIR / "v4_oos_reselected_merged.csv", index=False)
        print("merged recompute done:", len(oos_rows), "funds")

    summary = summarize(OUT_DIR)
    summary.to_csv(OUT_DIR / "v4_oos_summary.csv", index=False)
    print("saved summary")


def summarize(out_dir: Path) -> pd.DataFrame:
    rows = []
    for name in ["v4_oos_fixed_split_merged.csv", "v4_oos_reselected_merged.csv"]:
        path = out_dir / name
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "test_hit" not in df.columns:
            continue
        rows.append({
            "file": name,
            "funds": len(df),
            "test_hit_ge50": int((df["test_hit"] >= 0.50).sum()),
            "test_hit_ge55": int((df["test_hit"] >= 0.55).sum()),
            "test_avg_ge02": int((df["test_avg"].abs() >= 0.20).sum()),
            "test_avg_gt0": int((df["test_avg"] > 0).sum()),
            "test_trades_ge30": int((df["test_trades"] >= 30).sum()),
            "median_test_hit": float(df["test_hit"].median()),
            "median_test_avg": float(df["test_avg"].median()),
            "median_test_std": float(df["test_std"].median()),
            "median_test_trades": float(df["test_trades"].median()),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()



