"""Classify delivered strategies using current-code recomputed stats (not stale mapping CSV)."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def delivered_threshold(token: str) -> float:
    if token.startswith("self_5"):
        return 5.0
    if token.startswith("self_3"):
        return 3.0
    if token.startswith("self_big"):
        return 2.0
    if "_big_" in token:
        return 1.0
    if "gt2" in token or "lt-2" in token:
        return 2.0
    return 2.0


def suboptimal_map() -> dict[tuple[str, str, str, int], tuple[float, float, float, int]]:
    path = OUT_DIR / "v4_threshold_monotonic.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    out = {}
    for (tick, cond, tok, h), g in df.groupby(["ticker", "condition", "scan_token", "horizon"]):
        g = g.dropna(subset=["full_avg"])
        if g.empty:
            continue
        delivered = delivered_threshold(tok)
        drow = g[g["threshold"].eq(delivered)]
        if drow.empty:
            continue
        d_avg = float(drow["full_avg"].iloc[0])
        d_trades = int(drow["full_trades"].iloc[0])
        b = g.loc[g["full_avg"].idxmax()]
        best = float(b["threshold"])
        best_avg = float(b["full_avg"])
        best_trades = int(b["full_trades"])
        gain = best_avg - d_avg
        if gain >= 0.05 and best_trades >= 120:
            out[(tick, cond, tok, h)] = (delivered, best, best_avg, best_trades)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv", keep_default_na=False)
    oos = pd.read_csv(OUT_DIR / "v4_oos_fixed_split_by_strategy.csv")
    expl = pd.read_csv(OUT_DIR / "v4_strategy_explanation_v3.csv")
    mono = pd.read_csv(OUT_DIR / "v4_threshold_monotonic_summary.csv")
    sub = suboptimal_map()

    m = mapping[["ticker", "condition", "horizon", "source", "strategy_no"]].merge(
        oos[["ticker", "condition", "horizon", "full_avg", "full_hit", "full_trades", "full_std", "full_min", "full_tstat", "test_avg", "test_hit", "test_trades", "test_std"]],
        on=["ticker", "condition", "horizon"], how="left"
    )
    m = m.merge(expl[["ticker", "strategy_no", "fund_name", "fund_theme", "机制"]],
                on=["ticker", "strategy_no"], how="left")

    # compare mapping vs current-code recompute
    diff = mapping[["ticker", "condition", "horizon", "full_avg", "full_hit", "full_trades"]].merge(
        oos[["ticker", "condition", "horizon", "full_avg", "full_hit", "full_trades"]],
        on=["ticker", "condition", "horizon"], how="left", suffixes=("_mapping", "_recompute")
    )
    diff["avg_diff"] = diff["full_avg_mapping"] - diff["full_avg_recompute"]
    diff["hit_diff"] = diff["full_hit_mapping"] - diff["full_hit_recompute"]
    diff["trades_diff"] = diff["full_trades_mapping"] - diff["full_trades_recompute"]
    diff = diff[diff["avg_diff"].abs().gt(0.05) | diff["hit_diff"].abs().gt(0.03) | diff["trades_diff"].abs().gt(20)]
    diff.to_csv(OUT_DIR / "v4_mapping_vs_recompute_diff.csv", index=False)

    mono_by_key = {}
    for r in mono.itertuples(index=False):
        mono_by_key[(r.ticker, r.condition, r.scan_token, r.horizon)] = (r.monotone, r.spearman_like_rho)

    rows = []
    for r in m.itertuples(index=False):
        ticker = str(r.ticker)
        condition = str(r.condition)
        horizon = int(r.horizon)
        name = str(r.fund_name)
        theme = str(r.fund_theme)
        explanation = str(r.机制)
        tstat = float(r.full_tstat) if pd.notna(r.full_tstat) else float("nan")
        full_avg = float(r.full_avg)
        full_hit = float(r.full_hit)
        test_avg = float(r.test_avg) if pd.notna(r.test_avg) else float("nan")
        test_hit = float(r.test_hit) if pd.notna(r.test_hit) else float("nan")
        full_std = float(r.full_std) if pd.notna(r.full_std) else float("nan")
        full_min = float(r.full_min) if pd.notna(r.full_min) else float("nan")

        poor_train = bool((tstat < 2.0 and (full_avg < 0.25 or full_hit < 0.555)) or full_avg < 0.20 or full_hit < 0.55)
        high_std = bool((full_std > 3.5) or (full_min < -25))
        inverse = bool(("Short" in name) or ("Bear" in name) or ("UltraShort" in name) or ("Ultra Short" in name))
        direction_conflict = bool(inverse and ("风险偏好回暖，资金回流权益与信用资产" in explanation))
        btc_weak_link = bool(theme == "比特币")

        tokens = []
        for (tk, cond, tok, h), val in sub.items():
            if (tk, cond, h) == (ticker, condition, horizon):
                tokens.append((tok, val))
        threshold_suboptimal = bool(tokens)

        mono_flags = []
        for (tk, cond, tok, h), val in mono_by_key.items():
            if (tk, cond, h) == (ticker, condition, horizon):
                mono_flags.append(val)
        poor_mono = bool(mono_flags and any((not mo) or (rho is not None and not np.isnan(rho) and rho < 0.3) for mo, rho in mono_flags))

        if threshold_suboptimal:
            category = "need_improve"
            reason = "阈值可优化"
        elif direction_conflict:
            category = "need_improve"
            reason = "反向基金与风险偏好条件方向冲突"
        elif btc_weak_link:
            category = "excusable"
            reason = "无比特币参考ETF，条件只能依赖代理变量"
        elif poor_train and high_std and tstat < 1.5:
            category = "need_improve"
            reason = "训练效果弱且波动高"
        elif high_std and tstat >= 2.0 and inverse:
            category = "excusable"
            reason = "杠杆/反向产品本身波动高，但统计显著"
        elif poor_train and test_avg >= 0.4 and test_hit >= 0.62:
            category = "excusable"
            reason = "全历史偏弱但2025后表现强"
        elif poor_train:
            category = "need_improve"
            reason = "训练效果偏弱"
        else:
            category = "acceptable"
            reason = "各项指标可接受"

        rows.append({
            "ticker": ticker,
            "fund_name": name,
            "fund_theme": theme,
            "condition": condition,
            "horizon": horizon,
            "full_avg": full_avg,
            "full_hit": full_hit,
            "full_trades": int(r.full_trades),
            "test_avg": test_avg,
            "test_hit": test_hit,
            "full_tstat": tstat,
            "full_std": full_std,
            "full_min": full_min,
            "test_std": r.test_std,
            "poor_train": int(poor_train),
            "high_std": int(high_std),
            "poor_mono": int(poor_mono),
            "direction_conflict": int(direction_conflict),
            "btc_weak_link": int(btc_weak_link),
            "threshold_suboptimal": int(threshold_suboptimal),
            "category": category,
            "reason": reason,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "v4_strategy_review.csv", index=False)
    summary = df["category"].value_counts().rename_axis("category").reset_index(name="strategies")
    summary["pct"] = (summary["strategies"] / len(df) * 100).round(2)
    summary.to_csv(OUT_DIR / "v4_strategy_review_summary.csv", index=False)
    print("review rows:", len(df))
    print(summary.to_string(index=False))
    print("mapping diff rows:", len(diff))


if __name__ == "__main__":
    main()

