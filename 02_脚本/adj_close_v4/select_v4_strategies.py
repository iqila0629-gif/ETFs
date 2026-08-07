"""v4 Phase 4: select up to 3-5 strategies per fund and compare conflict rules."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_conditions as sc
import scan_v4_thresholds as s4


CUTOFF = np.datetime64("2025-01-01")
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
MAX_STRATEGIES = 5
MIN_STRATEGIES = 3
CANDIDATE_LIMIT = 60
DENSITY_TIERS = [(200, 40), (160, 35), (120, 30)]
TRIPLE_PATTERNS = {
    "up_up_up": (1, 1, 1),
    "down_down_down": (-1, -1, -1),
    "up_up_down": (1, 1, -1),
    "up_down_up": (1, -1, 1),
    "down_up_up": (-1, 1, 1),
    "down_down_up": (-1, -1, 1),
    "down_up_down": (-1, 1, -1),
    "up_down_down": (1, -1, -1),
}


def build_unified_mask(master: pd.DataFrame, condition: str, ticker: str, all_etfs: set[str]) -> pd.Series:
    if condition.startswith(("combo_", "ext_", "self_")):
        try:
            return sc.build_mask(master, condition, ticker)
        except Exception:
            return s4.build_condition_mask(master, condition, ticker, all_etfs)
    tokens = condition.split("_")
    if len(tokens) >= 6 and set(tokens[1:-2]) <= {"up", "down"}:
        a = tokens[0]
        pattern = "_".join(tokens[1:-2])
        b = tokens[-2]
        c = tokens[-1]
        signs = TRIPLE_PATTERNS.get(pattern)
        if signs and a in all_etfs and b in all_etfs and c in all_etfs:
            sa, sb, scc = signs
            ma = master[a] > 0 if sa == 1 else master[a] < 0
            mb = master[b] > 0 if sb == 1 else master[b] < 0
            mc = master[c] > 0 if scc == 1 else master[c] < 0
            return ma & mb & mc
    return s4.build_condition_mask(master, condition, ticker, all_etfs)


def signal_trades(master: pd.DataFrame, dates: np.ndarray, ticker: str, condition: str,
                  horizon: int, source: str, all_etfs: set[str], target_cache: dict) -> dict | None:
    mask = build_unified_mask(master, condition, ticker, all_etfs)
    strict = source in ("pair_scan", "triple_scan", "condition_expansion")
    key = (ticker, horizon, strict)
    if key not in target_cache:
        target_cache[key] = s4.multi_day_target(master, ticker, horizon, strict)
    target = target_cache[key]
    ev_dates, vals, trade_mask = s4.evaluate(mask, target, dates, *s4.params_for(source))
    if not trade_mask.any():
        return None
    td = pd.to_datetime(ev_dates[trade_mask])
    tv = vals[trade_mask]
    return {
        "condition": condition,
        "horizon": horizon,
        "source": source,
        "full_avg": float(tv.mean()),
        "full_trades": int(tv.size),
        "full_hit": float((tv > 0).mean()),
        "frozen_avg": float(tv[td >= CUTOFF].mean()) if (td >= CUTOFF).any() else float("nan"),
        "frozen_trades": int((td >= CUTOFF).sum()),
        "frozen_hit": float((tv[td >= CUTOFF] > 0).mean()) if (td >= CUTOFF).any() else float("nan"),
        "strength": abs(float(tv.mean())),
        "sign": 1 if float(tv.mean()) >= 0 else -1,
        "dates": set(td),
        "returns": dict(zip(td, tv)),
    }


def merge_stats(selected: list[dict]) -> dict:
    all_dates = set()
    for s in selected:
        all_dates |= s["dates"]
    by_date = {}
    for s in selected:
        for d, v in s["returns"].items():
            if d in all_dates:
                cur = by_date.get(d)
                if cur is None or s["strength"] > cur[1]:
                    by_date[d] = (v, s["strength"])
    ordered = sorted(all_dates)
    tv = np.array([by_date[d][0] for d in ordered], dtype=float)
    td = np.array(ordered, dtype="datetime64[ns]")
    hold = td >= CUTOFF
    return {
        "full_avg": float(tv.mean()),
        "full_trades": int(tv.size),
        "full_hit": float((tv > 0).mean()),
        "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
        "frozen_trades": int(hold.sum()),
        "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
    }


def rule_stats(selected: list[dict], rule: str) -> dict | None:
    all_dates = set()
    for s in selected:
        all_dates |= s["dates"]
    by_date = {}
    for d in all_dates:
        trading = [s for s in selected if d in s["dates"]]
        if rule == "R4_strongest":
            best = max(trading, key=lambda s: s["strength"])
            by_date[d] = best["returns"][d]
        elif rule == "majority_vote":
            ups = sum(1 for s in trading if s["sign"] == 1)
            downs = len(trading) - ups
            if ups == downs:
                continue
            want = 1 if ups > downs else -1
            best = max((s for s in trading if s["sign"] == want), key=lambda s: s["strength"])
            by_date[d] = best["returns"][d]
        elif rule == "priority_score":
            best = max(
                trading,
                key=lambda s: s["strength"] * max(s["full_hit"], 0.5) * np.log1p(s["full_trades"]),
            )
            by_date[d] = best["returns"][d]
        elif rule == "weighted":
            weight = sum(s["strength"] * s["sign"] for s in trading)
            if abs(weight) < 1e-12:
                continue
            want = 1 if weight > 0 else -1
            best = max((s for s in trading if s["sign"] == want), key=lambda s: s["strength"])
            by_date[d] = best["returns"][d]
        else:
            raise ValueError(rule)
    if not by_date:
        return None
    ordered = sorted(by_date)
    tv = np.array([by_date[d] for d in ordered], dtype=float)
    td = np.array(ordered, dtype="datetime64[ns]")
    hold = td >= CUTOFF
    return {
        "full_avg": float(tv.mean()),
        "full_trades": int(tv.size),
        "full_hit": float((tv > 0).mean()),
        "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
        "frozen_trades": int(hold.sum()),
        "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
    }


def constraints_ok(merged: dict, baseline: dict, density_full: int, density_frozen: int) -> bool:
    return bool(
        abs(merged["full_avg"]) >= max(0.9 * abs(baseline["full_avg"]), 0.2)
        and merged["full_hit"] >= baseline["full_hit"] - 0.03
        and merged["full_trades"] >= density_full
        and abs(merged["frozen_avg"]) >= max(0.9 * abs(baseline["frozen_avg"]), 0.2)
        and merged["frozen_hit"] >= baseline["frozen_hit"] - 0.03
        and merged["frozen_trades"] >= density_frozen
    )


def formal_pass(stats: dict) -> bool:
    return bool(
        abs(stats["full_avg"]) >= 0.2
        and stats["full_trades"] >= FULL_MIN
        and stats["full_hit"] > 0.55
        and stats["frozen_avg"] == stats["frozen_avg"]
        and abs(stats["frozen_avg"]) >= 0.2
        and stats["frozen_trades"] >= FROZEN_MIN
        and stats["frozen_hit"] >= 0.55
    )


def greedy_complement_sequence(cands: list[dict]) -> list[dict]:
    anchor = max(cands, key=lambda s: s["strength"] * np.sqrt(s["full_trades"]))
    seq = [anchor]
    current = set(anchor["dates"])
    for _ in range(MAX_STRATEGIES - 1):
        best = None
        best_gain = -1
        for c in cands:
            if c in seq:
                continue
            gain = len(c["dates"] - current)
            if gain > best_gain or (gain == best_gain and best is not None and c["strength"] > best["strength"]):
                best = c
                best_gain = gain
        if best is None or best_gain <= 0:
            break
        seq.append(best)
        current |= best["dates"]
    return seq


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)
    complement_mode = "--complement" in sys.argv
    suffix = "_complement" if complement_mode else "_density"

    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    fund_set = set(fund_cols)
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    dates = master["Date"].to_numpy()

    pool = pd.read_csv(config.V4_OUT / "v4_final20_combined_pass.csv", keep_default_na=False)
    keep_cols = ["ticker", "fund_group", "source", "condition", "horizon",
                 "full_avg", "full_trades", "full_hit",
                 "frozen_avg", "frozen_trades", "frozen_hit"]
    pool = pool[keep_cols]
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    print("final pool rows:", len(pool), "funds", pool["ticker"].nunique(), flush=True)

    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    mapping_rows = []
    selection_rows = []
    comparison_rows = []
    covered_tickers = []
    for ticker, group in pool.groupby("ticker", sort=True):
        cands = []
        for r in group.itertuples(index=False):
            rec = signal_trades(
                master, dates, ticker, str(r.condition), int(r.horizon),
                str(r.source), all_etfs, target_cache,
            )
            if rec is not None:
                cands.append(rec)
        if not cands:
            continue
        baseline = merge_stats(cands)
        score_order_all = sorted(cands, key=lambda s: (-s["strength"] * np.sqrt(s["full_trades"]), s["condition"]))

        selected = None
        selected_stats = None
        density_tier = None
        for dfull, dfrozen in DENSITY_TIERS:
            cands_tier = [
                c for c in cands
                if c["full_trades"] >= dfull and c["frozen_trades"] >= dfrozen
            ]
            if not cands_tier:
                continue
            if complement_mode:
                sequence = greedy_complement_sequence(cands_tier)
                for k in range(MIN_STRATEGIES, min(len(sequence), MAX_STRATEGIES) + 1):
                    trial = sequence[:k]
                    merged = merge_stats(trial)
                    if constraints_ok(merged, baseline, dfull, dfrozen):
                        selected = trial
                        selected_stats = merged
                        density_tier = (dfull, dfrozen)
                        break
            else:
                score_order = sorted(cands_tier, key=lambda s: (-s["strength"] * np.sqrt(s["full_trades"]), s["condition"]))
                trades_order = sorted(cands_tier, key=lambda s: (-s["full_trades"], s["condition"]))
                frozen_order = sorted(cands_tier, key=lambda s: (-s["frozen_trades"], s["condition"]))
                for order in [score_order, trades_order, frozen_order]:
                    for k in range(MIN_STRATEGIES, MAX_STRATEGIES + 1):
                        trial = order[:k]
                        merged = merge_stats(trial)
                        if constraints_ok(merged, baseline, dfull, dfrozen):
                            selected = trial
                            selected_stats = merged
                            density_tier = (dfull, dfrozen)
                            break
                    if selected is not None:
                        break
            if selected is not None:
                break
        if selected is None:
            selected = [score_order_all[0]]
            selected_stats = merge_stats(selected)
            density_tier = (FULL_MIN, FROZEN_MIN)
            met = formal_pass(selected_stats)
        else:
            met = True
        covered_tickers.append(ticker)

        for idx, s in enumerate(selected, start=1):
            mapping_rows.append(
                {
                    "ticker": ticker,
                    "strategy_no": idx,
                    "source": s["source"],
                    "condition": s["condition"],
                    "horizon": s["horizon"],
                    "full_avg": s["full_avg"],
                    "full_trades": s["full_trades"],
                    "full_hit": s["full_hit"],
                    "frozen_avg": s["frozen_avg"],
                    "frozen_trades": s["frozen_trades"],
                    "frozen_hit": s["frozen_hit"],
                    "density_full": density_tier[0],
                    "density_frozen": density_tier[1],
                }
            )
        selection_rows.append(
            {
                "ticker": ticker,
                "n_strategies": len(selected),
                "constraints_met": met,
                "base_full_avg": baseline["full_avg"],
                "base_full_trades": baseline["full_trades"],
                "base_full_hit": baseline["full_hit"],
                "base_frozen_avg": baseline["frozen_avg"],
                "base_frozen_trades": baseline["frozen_trades"],
                "base_frozen_hit": baseline["frozen_hit"],
                "sel_full_avg": selected_stats["full_avg"],
                "sel_full_trades": selected_stats["full_trades"],
                "sel_full_hit": selected_stats["full_hit"],
                "sel_frozen_avg": selected_stats["frozen_avg"],
                "sel_frozen_trades": selected_stats["frozen_trades"],
                "sel_frozen_hit": selected_stats["frozen_hit"],
                "density_full_req": density_tier[0],
                "density_frozen_req": density_tier[1],
            }
        )
        for rule in ["R4_strongest", "majority_vote", "priority_score", "weighted"]:
            stats = rule_stats(selected, rule)
            if stats is None:
                continue
            comparison_rows.append(
                {
                    "ticker": ticker,
                    "rule": rule,
                    **stats,
                }
            )
        if len(covered_tickers) % 20 == 0:
            print(f"selected {len(covered_tickers)} funds", flush=True)

    mapping = pd.DataFrame(mapping_rows)
    selection = pd.DataFrame(selection_rows)
    comparison = pd.DataFrame(comparison_rows)
    mapping.to_csv(config.V4_OUT / f"v4_strategy_mapping{suffix}.csv", index=False)
    selection.to_csv(config.V4_OUT / f"v4_strategy_selection{suffix}.csv", index=False)
    comparison.to_csv(config.V4_OUT / f"v4_conflict_rule_comparison{suffix}.csv", index=False)
    print("covered funds:", len(covered_tickers))
    print("selection constraints met:", int(selection["constraints_met"].sum()), "/", len(selection))
    print("avg strategies per fund:", round(selection["n_strategies"].mean(), 2))
    print("saved mapping/selection/comparison")


if __name__ == "__main__":
    main()
