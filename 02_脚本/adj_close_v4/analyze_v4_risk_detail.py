"""Detailed risk metrics for delivered m30 strategies and merged portfolios."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
METRICS = ["avg", "hit", "std", "ann_vol", "downside_std", "avg_std", "median", "p10", "p90", "max", "min", "tstat"]


def quantile_rows(df: pd.DataFrame, prefix: str, source: str) -> list[dict]:
    rows = []
    for m in METRICS:
        col = f"{prefix}_{m}"
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        rows.append({
            "source": source,
            "metric": m,
            "n": int(s.size),
            "min": float(s.min()),
            "p10": float(s.quantile(0.10)),
            "p25": float(s.quantile(0.25)),
            "median": float(s.median()),
            "p75": float(s.quantile(0.75)),
            "p90": float(s.quantile(0.90)),
            "max": float(s.max()),
        })
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_strategy = pd.read_csv(OUT_DIR / "v4_risk_by_strategy.csv")
    merged = pd.read_csv(OUT_DIR / "v4_risk_merged.csv")
    names = pd.read_csv(OUT_DIR / "v4_strategy_explanation_v3.csv")[["ticker", "fund_name", "fund_theme"]].drop_duplicates("ticker")
    uncond = pd.read_csv(OUT_DIR / "v4_fund_unconditional_stats.csv")

    rows = []
    for prefix, source in [("full", "strategy_full"), ("train", "strategy_train"), ("test", "strategy_test")]:
        rows += quantile_rows(by_strategy, prefix, source)
    for prefix, source in [("full", "merged_full"), ("train", "merged_train"), ("test", "merged_test")]:
        rows += quantile_rows(merged, prefix, source)
    pd.DataFrame(rows).to_csv(OUT_DIR / "v4_risk_distribution.csv", index=False)

    ratio = by_strategy[["ticker", "condition", "full_std", "full_avg_std"]].merge(
        uncond[["ticker", "std", "avg_std"]], on="ticker", how="left"
    )
    ratio["std_ratio"] = ratio["full_std"] / ratio["std"]
    ratio["avgstd_ratio"] = ratio["full_avg_std"] / ratio["avg_std"]
    ratio["std_ratio_band"] = pd.cut(
        ratio["std_ratio"], bins=[-np.inf, 0.5, 1.0, 1.5, 2.0, np.inf],
        labels=["<0.5x", "0.5-1.0x", "1.0-1.5x", "1.5-2.0x", ">2.0x"],
    )
    summary = ratio["std_ratio_band"].value_counts().rename_axis("band").reset_index(name="strategies")
    summary["pct"] = (summary["strategies"] / len(ratio) * 100).round(2)
    summary.to_csv(OUT_DIR / "v4_risk_ratio_summary.csv", index=False)
    ratio.to_csv(OUT_DIR / "v4_risk_ratio_by_strategy.csv", index=False)

    worst_rows = []
    by = by_strategy.merge(names, on="ticker", how="left")
    for label, col, asc in [
        ("full_std_max", "full_std", False),
        ("ann_vol_max", "full_ann_vol", False),
        ("loss_max", "full_min", True),
        ("test_std_max", "test_std", False),
        ("tstat_max", "full_tstat", False),
        ("tstat_min", "full_tstat", True),
    ]:
        sub = by.nlargest(10, col) if not asc else by.nsmallest(10, col)
        for _, r in sub.iterrows():
            worst_rows.append({
                "list": label,
                "ticker": r["ticker"],
                "fund_name": r["fund_name"],
                "fund_theme": r["fund_theme"],
                "condition": r["condition"],
                "value": r[col],
            })
    pd.DataFrame(worst_rows).to_csv(OUT_DIR / "v4_risk_worst.csv", index=False)

    flags = by[["ticker", "fund_name", "fund_theme", "condition", "full_std", "full_avg", "full_hit", "train_std", "test_std", "flag_std_high", "flag_avgstd_low", "flag_test_std_high"]]
    flags = flags[(flags["flag_std_high"] == 1) | (flags["flag_avgstd_low"] == 1) | (flags["flag_test_std_high"] == 1)]
    flags.to_csv(OUT_DIR / "v4_risk_flags_detail.csv", index=False)
    print("risk detail saved; flag strategies:", len(flags))


if __name__ == "__main__":
    main()

