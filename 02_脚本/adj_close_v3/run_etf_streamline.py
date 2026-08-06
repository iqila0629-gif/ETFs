"""Data-driven ETF subset evaluation for the formal signal pool.

No ETF is treated as mandatory. Every subset is scored on the existing formal
signal pool by re-selecting each fund's best strategy and checking coverage and
quality.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
EVENT = ROOT.parent / "event_study"
DELIV = ROOT / "delivery_preview"
OUT = ROOT / "etf_streamline_formal"

sys.path.insert(0, str(EVENT))

from build_v3_delivery import (  # noqa: E402
    CUTOFF,
    build_master,
    evaluate_signal,
    get_target,
    params_for,
    write_wide,
)
from event_metrics import fund_group  # noqa: E402


def load_pool() -> pd.DataFrame:
    pool = pd.read_csv(DELIV / "全部ETF" / "成果" / "v3_正式信号_全量.csv", keep_default_na=False)
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    pool["abs_full_avg"] = pool["full_avg"].abs()
    return pool


def etf_list_from_usage() -> list[str]:
    usage = pd.read_csv(DELIV / "全部ETF" / "成果" / "v3_ETF使用统计.csv")
    return [str(e) for e in usage["ETF"].tolist()]


def all_non_money_tickers() -> list[str]:
    panel = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in panel.columns:
        panel = panel.rename(columns={"date": "Date"})
    return [c for c in panel.columns[1:] if c not in {"MPIXX", "MPSXX"}]


def build_signal_requirements(pool: pd.DataFrame, etfs: list[str]) -> tuple[np.ndarray, np.ndarray]:
    etf_set = set(etfs)
    bit = {e: 1 << i for i, e in enumerate(etfs)}
    reqs = []
    for cond in pool["condition"]:
        mask = 0
        for token in str(cond).split("_"):
            if token in etf_set:
                mask |= bit[token]
        reqs.append(mask)
    mask64 = (1 << 64) - 1
    req_lo = np.asarray([r & mask64 for r in reqs], dtype=np.uint64)
    req_hi = np.asarray([r >> 64 for r in reqs], dtype=np.uint64)
    return req_lo, req_hi


def popcount(x: int) -> int:
    return x.bit_count()


class SubsetEvaluator:
    def __init__(self, pool: pd.DataFrame, reqs: tuple[np.ndarray, np.ndarray], etfs: list[str]):
        self.pool = pool
        self.req_lo, self.req_hi = reqs
        self.etfs = etfs
        self.all_bits = (1 << len(etfs)) - 1
        self.mask64 = (1 << 64) - 1
        self._full_cache: dict[int, dict] = {}
        self._cov_cache: dict[int, int] = {}

        df = pool.copy()
        df["_req_lo"] = reqs[0]
        df["_req_hi"] = reqs[1]
        df = df.sort_values(
            ["ticker", "abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=[True, False, False, False, False],
        ).reset_index(drop=True)
        self.df = df
        self.sorted_req_lo = df["_req_lo"].to_numpy(dtype=np.uint64)
        self.sorted_req_hi = df["_req_hi"].to_numpy(dtype=np.uint64)
        self.ticker = df["ticker"].to_numpy()
        codes, uniques = pd.factorize(df["ticker"])
        self.codes = codes
        self.unique_tickers = list(uniques)
        self.starts = {}
        self.ends = {}
        for code, name in enumerate(uniques):
            idx = np.flatnonzero(codes == code)
            self.starts[name] = int(idx[0])
            self.ends[name] = int(idx[-1]) + 1
        self.all_tickers = all_non_money_tickers()

    def _avail(self, subset: int) -> np.ndarray:
        sub_lo = subset & self.mask64
        sub_hi = subset >> 64
        not_lo = self.mask64 ^ sub_lo
        not_hi = self.mask64 ^ sub_hi
        return ((self.sorted_req_lo & np.uint64(not_lo)) == 0) & (
            (self.sorted_req_hi & np.uint64(not_hi)) == 0
        )

    def coverage(self, subset: int) -> int:
        if subset in self._cov_cache:
            return self._cov_cache[subset]
        avail = self._avail(subset)
        cov = 0
        for name in self.all_tickers:
            s = self.starts.get(name)
            if s is not None and avail[s : self.ends[name]].any():
                cov += 1
        self._cov_cache[subset] = cov
        return cov

    def evaluate(self, subset: int) -> dict:
        if subset in self._full_cache:
            return self._full_cache[subset]
        avail = self._avail(subset)
        best_idx = []
        for name in self.all_tickers:
            s = self.starts.get(name)
            if s is None:
                continue
            block = np.flatnonzero(avail[s : self.ends[name]])
            if block.size:
                best_idx.append(s + int(block[0]))
        covered = len(best_idx)
        best = self.df.iloc[best_idx]
        rec = {
            "subset_bits": subset,
            "etf_count": popcount(subset),
            "covered_funds": covered,
            "available_signals": int(avail.sum()),
            "uncovered_funds": len(self.all_tickers) - covered,
            "median_full_hit": float(best["full_hit"].median()) if covered else float("nan"),
            "min_full_hit": float(best["full_hit"].min()) if covered else float("nan"),
            "median_frozen_hit": float(best["frozen_hit"].median()) if covered else float("nan"),
            "min_frozen_hit": float(best["frozen_hit"].min()) if covered else float("nan"),
            "median_full_avg_abs": float(best["full_avg"].abs().median()) if covered else float("nan"),
            "median_frozen_avg_abs": float(best["frozen_avg"].abs().median()) if covered else float("nan"),
            "median_frozen_trades": float(best["frozen_trades"].median()) if covered else float("nan"),
            "best_tickers": [str(t) for t in best["ticker"].tolist()],
            "best_conditions": [str(c) for c in best["condition"].tolist()],
            "best_horizons": [int(h) for h in best["horizon"].tolist()],
        }
        self._full_cache[subset] = rec
        self._cov_cache[subset] = covered
        return rec

    def subset_etfs(self, subset: int) -> list[str]:
        return [e for i, e in enumerate(self.etfs) if subset & (1 << i)]


def better_tie(a: dict, b: dict) -> bool:
    if a["median_frozen_hit"] != b["median_frozen_hit"]:
        return a["median_frozen_hit"] > b["median_frozen_hit"]
    if a["median_full_hit"] != b["median_full_hit"]:
        return a["median_full_hit"] > b["median_full_hit"]
    if a["median_full_avg_abs"] != b["median_full_avg_abs"]:
        return a["median_full_avg_abs"] > b["median_full_avg_abs"]
    return a["etf_count"] < b["etf_count"]


def forward_greedy(ev: SubsetEvaluator, initial: int = 0, target: int = 119) -> list[dict]:
    subset = initial
    results = [ev.evaluate(subset)]
    for _ in range(len(ev.etfs) - popcount(subset)):
        remaining = [1 << i for i in range(len(ev.etfs)) if not (subset & (1 << i))]
        if not remaining:
            break
        best_cov = -1
        best_cands = []
        for bit in remaining:
            cov = ev.coverage(subset | bit)
            if cov > best_cov:
                best_cov = cov
                best_cands = [bit]
            elif cov == best_cov:
                best_cands.append(bit)
        if best_cov <= ev.coverage(subset):
            break
        if len(best_cands) > 1:
            cand_recs = [ev.evaluate(subset | bit) for bit in best_cands]
            best_bit = best_cands[0]
            best_rec = cand_recs[0]
            for bit, rec in zip(best_cands[1:], cand_recs[1:]):
                if better_tie(rec, best_rec):
                    best_bit = bit
                    best_rec = rec
        else:
            best_bit = best_cands[0]
        subset |= best_bit
        results.append(ev.evaluate(subset))
        if ev.coverage(subset) >= target and len(results) >= 2:
            pass
    return results


def backward_elimination(ev: SubsetEvaluator, target: int = 119) -> list[dict]:
    subset = ev.all_bits
    results = [ev.evaluate(subset)]
    while popcount(subset) > 1:
        removals = [1 << i for i in range(len(ev.etfs)) if subset & (1 << i)]
        best_cov = -1
        best_cands = []
        for bit in removals:
            cand = subset ^ bit
            cov = ev.coverage(cand)
            if cov > best_cov:
                best_cov = cov
                best_cands = [bit]
            elif cov == best_cov:
                best_cands.append(bit)
        if best_cov < target:
            break
        if len(best_cands) > 1:
            cand_recs = [ev.evaluate(subset ^ bit) for bit in best_cands]
            best_bit = best_cands[0]
            best_rec = cand_recs[0]
            for bit, rec in zip(best_cands[1:], cand_recs[1:]):
                if better_tie(rec, best_rec):
                    best_bit = bit
                    best_rec = rec
        else:
            best_bit = best_cands[0]
        subset ^= best_bit
        results.append(ev.evaluate(subset))
    return results


def randomized_greedy(ev: SubsetEvaluator, target: int = 119, restarts: int = 30) -> list[dict]:
    rng = np.random.default_rng(20260805)
    results = []
    for _ in range(restarts):
        subset = 0
        add_steps = rng.integers(0, 16)
        for _ in range(add_steps):
            remaining = [1 << i for i in range(len(ev.etfs)) if not (subset & (1 << i))]
            if not remaining:
                break
            subset |= int(rng.choice(remaining))
        # Greedy add until target or no improvement.
        for _ in range(len(ev.etfs) - popcount(subset)):
            remaining = [1 << i for i in range(len(ev.etfs)) if not (subset & (1 << i))]
            if not remaining:
                break
            sample = list(rng.choice(remaining, size=min(15, len(remaining)), replace=False))
            best_cov = -1
            best_bit = None
            for bit in sample:
                cov = ev.coverage(subset | bit)
                if cov > best_cov:
                    best_cov = cov
                    best_bit = bit
            if best_bit is None or best_cov <= ev.coverage(subset):
                break
            subset |= best_bit
        # Greedy remove while coverage holds.
        while popcount(subset) > 1:
            removals = [1 << i for i in range(len(ev.etfs)) if subset & (1 << i)]
            best_cov = -1
            best_bit = None
            for bit in removals:
                cov = ev.coverage(subset ^ bit)
                if cov > best_cov:
                    best_cov = cov
                    best_bit = bit
            if best_bit is None or best_cov < target:
                break
            subset ^= best_bit
        if subset not in ev._full_cache:
            results.append(ev.evaluate(subset))
    return results


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)

    print("loading formal signal pool", flush=True)
    pool = load_pool()
    etfs = etf_list_from_usage()
    reqs = build_signal_requirements(pool, etfs)
    ev = SubsetEvaluator(pool, reqs, etfs)

    original_bits = 0
    for i, e in enumerate(etfs):
        if e in {
            "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP",
            "SLV", "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
        }:
            original_bits |= 1 << i

    print("running forward greedy from empty", flush=True)
    forward = forward_greedy(ev, 0)
    print("running backward elimination from all 76", flush=True)
    backward = backward_elimination(ev)
    print("running randomized restarts", flush=True)
    random_subsets = randomized_greedy(ev, restarts=200)

    baselines = [
        ev.evaluate(0),
        ev.evaluate(original_bits),
        ev.evaluate(ev.all_bits),
    ]
    all_recs = baselines + forward + backward + random_subsets
    dedup: dict[int, dict] = {}
    for rec in all_recs:
        dedup[rec["subset_bits"]] = rec
    scan = pd.DataFrame(list(dedup.values()))
    scan["avg_min"] = scan[["median_full_avg_abs", "median_frozen_avg_abs"]].min(axis=1)
    scan = scan.sort_values(
        ["covered_funds", "etf_count", "median_frozen_hit"],
        ascending=[False, True, False],
    )
    scan.to_csv(OUT / "etf_subset_scan.csv", index=False)

    pareto_rows = []
    for cov, grp in scan.groupby("covered_funds"):
        row = grp.sort_values(["etf_count", "median_frozen_hit"], ascending=[True, False]).iloc[0]
        pareto_rows.append(row)
    pareto = pd.DataFrame(pareto_rows).sort_values("covered_funds", ascending=False)
    pareto.to_csv(OUT / "etf_pareto.csv", index=False)

    target = 119
    target_avg = 0.5
    candidates = scan[
        (scan["covered_funds"] >= target)
        & (scan["median_full_avg_abs"] >= target_avg)
        & (scan["median_frozen_avg_abs"] >= target_avg)
    ]
    if len(candidates):
        selected = candidates.sort_values(
            ["etf_count", "median_frozen_hit", "median_full_hit", "avg_min"],
            ascending=[True, False, False, False],
        ).iloc[0]
    else:
        selected = scan[scan["covered_funds"] >= target].sort_values(
            ["etf_count", "median_frozen_hit", "median_full_hit"],
            ascending=[True, False, False],
        ).iloc[0]
    selected_bits = int(selected["subset_bits"])
    selected_rec = ev.evaluate(selected_bits)
    selected_etfs = ev.subset_etfs(selected_bits)
    pd.DataFrame({"ETF": selected_etfs}).to_csv(OUT / "etf_streamlined_list.csv", index=False)

    best_rows = []
    for t, c, h in zip(
        selected_rec["best_tickers"],
        selected_rec["best_conditions"],
        selected_rec["best_horizons"],
    ):
        row = ev.pool[
            (ev.pool["ticker"] == t)
            & (ev.pool["condition"] == c)
            & (ev.pool["horizon"] == h)
        ].iloc[0]
        best_rows.append(row)
    best_df = pd.DataFrame(best_rows).drop_duplicates(["ticker", "condition", "horizon"])
    best_df = best_df.sort_values("ticker").reset_index(drop=True)
    best_df["decision"] = np.where(best_df["full_avg"] > 0, "predict_up", "predict_down")
    best_df.to_csv(OUT / "etf_streamlined_best_strategies.csv", index=False)

    options_rows = []
    for n in range(14, 36):
        sub = scan[(scan["covered_funds"] >= target) & (scan["etf_count"] == n)]
        if sub.empty:
            continue
        opt = sub.sort_values(
            ["avg_min", "median_frozen_hit", "median_full_hit"],
            ascending=[False, False, False],
        ).iloc[0]
        opt_row = opt.to_dict()
        opt_row["etf_list"] = ", ".join(ev.subset_etfs(int(opt["subset_bits"])))
        options_rows.append(opt_row)
    pd.DataFrame(options_rows).to_csv(OUT / "etf_streamlined_options.csv", index=False)

    # Company-format wide tables for the selected subset.
    master = build_master()
    all_tickers = all_non_money_tickers()
    all_etfs = set(etfs)
    dates = master["Date"].to_numpy()
    dates_desc = list(pd.to_datetime(master["Date"]).sort_values(ascending=False))
    by_fund: dict[str, dict[pd.Timestamp, float]] = {t: {} for t in all_tickers}
    detail: list[dict] = []
    cache: dict[tuple[str, str | None], pd.Series] = {}

    def mask_for(condition: str, ticker: str) -> pd.Series:
        key = (condition, ticker if condition.startswith("self_") else None)
        if key not in cache:
            from build_v3_delivery import build_condition_mask

            cache[key] = build_condition_mask(master, condition, ticker, all_etfs)
        return cache[key]

    for _, row in best_df.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        source = str(row["source"])
        mask = mask_for(condition, ticker)
        target_arr = get_target(master, ticker, horizon, strict_finite=source.startswith("pair_scan"))
        ev_dates, vals, tm, pred = evaluate_signal(mask, target_arr, dates, *params_for(source))
        if not tm.any():
            continue
        for d, v, pr in zip(ev_dates[tm], vals[tm], pred[tm]):
            by_fund[ticker][pd.Timestamp(d)] = float(v)
            detail.append(
                {
                    "ticker": ticker,
                    "condition": condition,
                    "horizon": horizon,
                    "date": pd.Timestamp(d).strftime("%m/%d/%Y"),
                    "predicted_return": float(pr),
                    "actual_return": float(v),
                }
            )
    pd.DataFrame(detail).to_csv(OUT / "etf_streamlined_signal_detail.csv", index=False)
    write_wide(OUT / "etf_streamlined_company_full_history.csv", dates_desc, all_tickers, by_fund)
    frozen = {
        t: {d: v for d, v in m.items() if d >= pd.Timestamp(CUTOFF)}
        for t, m in by_fund.items()
    }
    write_wide(
        OUT / "etf_streamlined_company_frozen.csv",
        [d for d in dates_desc if d >= pd.Timestamp(CUTOFF)],
        all_tickers,
        frozen,
    )

    # Usage stats.
    usage_rows = []
    for i, e in enumerate(etfs):
        bit = 1 << i
        bit_lo = bit & ev.mask64
        bit_hi = bit >> 64
        has = ((ev.req_lo & np.uint64(bit_lo)) != 0) | ((ev.req_hi & np.uint64(bit_hi)) != 0)
        usage_rows.append(
            {
                "ETF": e,
                "in_original19": e in {
                    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP",
                    "SLV", "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
                },
                "in_selected": e in selected_etfs,
                "all_signals": int(has.sum()),
                "all_funds": int(ev.pool.loc[has, "ticker"].nunique()),
                "selected_best_signals": int(best_df["condition"].apply(lambda c: e in str(c).split("_")).sum()),
            }
        )
    pd.DataFrame(usage_rows).sort_values(
        ["selected_best_signals", "all_signals"], ascending=False
    ).to_csv(OUT / "etf_usage_rank.csv", index=False)

    full_wide = pd.read_csv(OUT / "etf_streamlined_company_full_history.csv", skiprows=12)
    frozen_wide = pd.read_csv(OUT / "etf_streamlined_company_frozen.csv", skiprows=12)
    full_ok = 0
    frozen_ok = 0
    for col in full_wide.columns[1:]:
        vals = full_wide[col].dropna()
        if not vals.empty and abs(vals.mean()) >= 0.2 and len(vals) >= 50 and (vals > 0).mean() >= 0.55:
            full_ok += 1
    for col in frozen_wide.columns[1:]:
        vals = frozen_wide[col].dropna()
        if not vals.empty and abs(vals.mean()) >= 0.2 and len(vals) >= 10 and (vals > 0).mean() >= 0.55:
            frozen_ok += 1

    report = (
        "# 正式版本 ETF 精简结果\n\n"
        f"日期：2026-08-05\n\n"
        f"正式信号池：{len(pool)} 个，覆盖 {pool['ticker'].nunique()} 支基金\n"
        f"目标覆盖：119 支非货币基金\n\n"
        f"## 方法\n\n"
        f"- 在现有正式信号池上按 ETF 子集重选每基金最佳策略；\n"
        f"- 方法包括：空集正向贪心、76 支反向淘汰、200 次随机重启；\n"
        f"- 没有把任何一支 ETF 设为“必须保留”；\n"
        f"- 选择条件：覆盖 119 支，且全历史/冻结期 Average 中位数均不低于 0.50%。\n\n"
        f"## 基线\n\n"
        f"- 空 ETF（只靠外部/自身信号）：覆盖 {ev.evaluate(0)['covered_funds']} 支\n"
        f"- 原始 19 支：覆盖 {ev.evaluate(original_bits)['covered_funds']} 支，"
        f"冻结期命中率中位数 {ev.evaluate(original_bits)['median_frozen_hit']:.4f}，"
        f"全历史命中率中位数 {ev.evaluate(original_bits)['median_full_hit']:.4f}\n"
        f"- 全部 76 支：覆盖 {ev.evaluate(ev.all_bits)['covered_funds']} 支，"
        f"冻结期命中率中位数 {ev.evaluate(ev.all_bits)['median_frozen_hit']:.4f}，"
        f"全历史命中率中位数 {ev.evaluate(ev.all_bits)['median_full_hit']:.4f}\n\n"
        f"## 最优子集\n\n"
        f"- ETF 数量：{selected_rec['etf_count']}\n"
        f"- 覆盖基金：{selected_rec['covered_funds']}\n"
        f"- 可用信号：{selected_rec['available_signals']}\n"
        f"- 冻结期命中率中位数：{selected_rec['median_frozen_hit']:.4f}\n"
        f"- 全历史命中率中位数：{selected_rec['median_full_hit']:.4f}\n"
        f"- 全历史Average中位数：{selected_rec['median_full_avg_abs']:.4f}\n"
        f"- 冻结期Average中位数：{selected_rec['median_frozen_avg_abs']:.4f}\n"
        f"- Average选择标准：全历史与冻结期中位数均不低于 0.50%\n"
        f"- ETF 列表：{', '.join(selected_etfs)}\n\n"
        f"## 校验\n\n"
        f"- 最佳策略：{len(best_df)} 条，覆盖 {best_df['ticker'].nunique()} 支基金\n"
        f"- 全历史宽表达标：{full_ok}/119\n"
        f"- 冻结期宽表达标：{frozen_ok}/119\n\n"
        f"## 可选清单（覆盖 119 支）\n\n"
        + "\n".join(
            f"- {int(o['etf_count'])} 支：冻结期命中率中位数 {float(o['median_frozen_hit']):.4f}，"
            f"全历史命中率中位数 {float(o['median_full_hit']):.4f}，"
            f"全历史Average中位数 {float(o['median_full_avg_abs']):.4f}，"
            f"冻结期Average中位数 {float(o['median_frozen_avg_abs']):.4f}，"
            f"可用信号 {int(o['available_signals'])}"
            for o in options_rows[:10]
        )
        + "\n\n"
        f"## 结论\n\n"
        f"原始 ETF 清单不作为约束；最优子集由覆盖数、命中率和 Average 共同决定。\n"
        f"在覆盖 119 支的前提下，ETF 数量越少命中率中位数越低；\n"
        f"可选清单见 etf_streamlined_options.csv。\n"
        f"详细扫描和帕累托前沿见 etf_subset_scan.csv / etf_pareto.csv。\n"
    )
    (OUT / "etf_streamlined_报告.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
