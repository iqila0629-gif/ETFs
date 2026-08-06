"""Diagnose v4 uncovered funds and evaluate 1-3 extended ETF additions."""

from __future__ import annotations

import itertools
import sys

import numpy as np
import pandas as pd

import config


MIN_ABS_AVG = 0.2
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55


def load_pools() -> pd.DataFrame:
    recomputed = config.V4_OUT / "v4_76pool_recomputed.csv"
    if recomputed.exists():
        return pd.read_csv(recomputed, keep_default_na=False).reset_index(drop=True)
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


def fund_group(ticker: str) -> str:
    if ticker.endswith("SX"):
        return "inverse"
    if ticker.startswith("U"):
        return "ultra_long"
    return "long"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    fund_panel = pd.read_csv(config.FUND_PANEL)
    if "date" in fund_panel.columns:
        fund_panel = fund_panel.rename(columns={"date": "Date"})
    fund_panel["Date"] = pd.to_datetime(fund_panel["Date"])
    all_tickers = list(fund_panel.columns[1:])

    best_path = config.V4_OUT / "v4_allmethods_best_strategy.csv"
    if not best_path.exists():
        best_path = config.V4_OUT / "v4_phase3_best_strategy.csv"
    best = pd.read_csv(best_path, keep_default_na=False)
    covered = set(best["ticker"])
    uncovered = [
        t for t in all_tickers if t not in covered and t not in config.MONEY_FUNDS
    ]
    print("uncovered funds:", len(uncovered))

    pool = load_pools()
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    all_known_etf_tokens = {
        t
        for c in pool["condition"]
        for t in str(c).split("_")
        if t.isupper() and len(t) in (3, 4)
    }
    extended = sorted(all_known_etf_tokens - config.ORIGINAL19)
    print("extended ETF tokens in pools:", len(extended))

    def etf_tokens(cond: str) -> set[str]:
        return {t for t in str(cond).split("_") if t in all_known_etf_tokens}

    pool["etf_tokens"] = pool["condition"].apply(etf_tokens)
    pool["full_ok"] = (
        pool["full_avg"].abs().ge(MIN_ABS_AVG)
        & pool["full_trades"].ge(FULL_MIN)
        & pool["full_hit"].gt(MIN_FULL_HIT)
    )
    pool["frozen_ok"] = (
        pool["frozen_avg"].abs().ge(MIN_ABS_AVG)
        & pool["frozen_trades"].ge(FROZEN_MIN)
        & pool["frozen_hit"].ge(MIN_FROZEN_HIT)
    )
    pool["pass"] = pool["full_ok"] & pool["frozen_ok"]

    diag_rows = []
    for ticker in uncovered:
        vals = fund_panel[ticker].to_numpy(dtype=float)
        obs = int(np.isfinite(vals).sum())
        valid = vals[np.isfinite(vals)]
        vol = float(np.std(valid) * 100) if valid.size else float("nan")
        mean_abs = float(np.mean(np.abs(valid)) * 100) if valid.size else float("nan")
        sub = pool[pool["ticker"] == ticker]
        if len(sub):
            max_full_trades = int(sub["full_trades"].max())
            max_frozen_trades = int(sub["frozen_trades"].max())
            best_full_avg_abs = float(sub["full_avg"].abs().max())
            best_frozen_avg_abs = float(sub["frozen_avg"].abs().max())
            best_full_hit = float(sub["full_hit"].max())
            best_frozen_hit = float(sub["frozen_hit"].max())
            any_pass = bool(sub["pass"].any())
            pass_rows = sub[sub["pass"]]
            if any_pass:
                reason = "pass_76_pool"
                best_cond = str(pass_rows.sort_values(["full_avg", "frozen_hit"], ascending=False).iloc[0]["condition"])
                best_ext = sorted(set().union(*[r["etf_tokens"] for _, r in pass_rows.iterrows()]) - config.ORIGINAL19)
            else:
                best_row = sub.assign(
                    abs_full_avg=sub["full_avg"].abs(),
                    abs_frozen_avg=sub["frozen_avg"].abs(),
                ).sort_values(["abs_full_avg", "frozen_hit"], ascending=False).iloc[0]
                blockers = []
                if abs(float(best_row["full_avg"])) < MIN_ABS_AVG:
                    blockers.append("full_avg")
                if int(best_row["full_trades"]) < FULL_MIN:
                    blockers.append("full_trades")
                if float(best_row["full_hit"]) <= MIN_FULL_HIT:
                    blockers.append("full_hit")
                if abs(float(best_row["frozen_avg"])) < MIN_ABS_AVG:
                    blockers.append("frozen_avg")
                if int(best_row["frozen_trades"]) < FROZEN_MIN:
                    blockers.append("frozen_trades")
                if float(best_row["frozen_hit"]) < MIN_FROZEN_HIT:
                    blockers.append("frozen_hit")
                trade_ok = sub["full_trades"].ge(FULL_MIN) & sub["frozen_trades"].ge(FROZEN_MIN)
                quality_ok = (
                    sub["full_avg"].abs().ge(MIN_ABS_AVG)
                    & sub["full_hit"].gt(MIN_FULL_HIT)
                    & sub["frozen_avg"].abs().ge(MIN_ABS_AVG)
                    & sub["frozen_hit"].ge(MIN_FROZEN_HIT)
                )
                trade_blocked = int((quality_ok & ~trade_ok).sum())
                quality_blocked = int((~quality_ok & trade_ok).sum())
                if trade_blocked and not quality_blocked:
                    reason = "trade_count"
                elif quality_blocked and not trade_blocked:
                    reason = "avg_hit"
                elif trade_blocked:
                    reason = "avg_hit_and_trades"
                else:
                    reason = "avg_hit"
                best_cond = ""
                best_ext = []
        else:
            max_full_trades = 0
            max_frozen_trades = 0
            best_full_avg_abs = 0.0
            best_frozen_avg_abs = 0.0
            best_full_hit = 0.0
            best_frozen_hit = 0.0
            any_pass = False
            reason = "no_candidate"
            best_cond = ""
            best_ext = []
        diag_rows.append(
            {
                "ticker": ticker,
                "fund_group": fund_group(ticker),
                "obs": obs,
                "daily_vol_pct": vol,
                "mean_abs_return_pct": mean_abs,
                "candidates": len(sub),
                "max_full_trades": max_full_trades,
                "max_frozen_trades": max_frozen_trades,
                "best_full_avg_abs": best_full_avg_abs,
                "best_frozen_avg_abs": best_frozen_avg_abs,
                "best_full_hit": best_full_hit,
                "best_frozen_hit": best_frozen_hit,
                "pass_in_76_pool": any_pass,
                "reason": reason,
                "best_condition": best_cond,
                "needed_ext_etfs": "|".join(best_ext),
            }
        )
    diag = pd.DataFrame(diag_rows).sort_values("ticker").reset_index(drop=True)
    diag.to_csv(config.V4_OUT / "v4_gap_diagnosis.csv", index=False)
    print("diagnosis saved:", config.V4_OUT / "v4_gap_diagnosis.csv")
    print(diag[["ticker", "fund_group", "obs", "max_full_trades", "max_frozen_trades", "reason", "needed_ext_etfs"]].to_string(index=False))

    # Extended ETF set cover: uncovered funds with a 120/30 pass in the 76 pool.
    coverable = diag[diag["reason"] == "pass_76_pool"]
    coverable_funds = set(coverable["ticker"])
    print("\nfunds coverable by extending ETF universe:", len(coverable_funds))

    fund_reqs: dict[str, list[frozenset[str]]] = {}
    for fund in coverable_funds:
        sub = pool[(pool["ticker"] == fund) & pool["pass"]]
        reqs = {frozenset(r["etf_tokens"] - config.ORIGINAL19) for _, r in sub.iterrows()}
        fund_reqs[fund] = sorted(reqs, key=len)

    def funds_covered_by(etf_set: set[str]) -> set[str]:
        out = set()
        for fund, reqs in fund_reqs.items():
            if any(req <= etf_set for req in reqs):
                out.add(fund)
        return out

    single_rows = []
    for etf in extended:
        got = funds_covered_by({etf})
        single_rows.append({"etf": etf, "covered_funds": len(got), "funds": "|".join(sorted(got))})
    single = pd.DataFrame(single_rows).sort_values(["covered_funds", "etf"], ascending=False).reset_index(drop=True)
    print("\ntop extended ETFs by uncovered funds covered:")
    print(single.head(15).to_string(index=False))

    greedy = set()
    greedy_log = []
    for _ in range(3):
        best_etf = None
        best_gain = -1
        best_funds = set()
        for etf in extended:
            if etf in greedy:
                continue
            got = funds_covered_by(greedy | {etf})
            gain = len(got - funds_covered_by(greedy))
            if gain > best_gain:
                best_etf = etf
                best_gain = gain
                best_funds = got
        if best_etf is None:
            break
        greedy.add(best_etf)
        greedy_log.append({"etf": best_etf, "gain": best_gain, "total_covered": len(best_funds), "funds": "|".join(sorted(best_funds))})
    greedy_df = pd.DataFrame(greedy_log)
    print("\ngreedy 1-3 ETF expansion:")
    print(greedy_df.to_string(index=False))

    best_combos = []
    for size in (1, 2, 3):
        for combo in itertools.combinations(extended, size):
            got = funds_covered_by(set(combo))
            best_combos.append(
                {
                    "size": size,
                    "etfs": "|".join(sorted(combo)),
                    "covered_funds": len(got),
                    "funds": "|".join(sorted(got)),
                }
            )
    combos = pd.DataFrame(best_combos).sort_values(["covered_funds", "size"], ascending=[False, True]).reset_index(drop=True)
    combos.head(20).to_csv(config.V4_OUT / "v4_extended_etf_expansion.csv", index=False)
    print("\nbest combos (top 20):")
    print(combos.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
