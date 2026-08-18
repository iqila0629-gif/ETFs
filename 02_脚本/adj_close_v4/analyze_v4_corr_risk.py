"""v4 robustness: variable correlations and risk metrics for delivered m30 strategies."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
FUND_NAMES = config.ROOT / "04_结果" / "最新成果" / "中间文档" / "通用" / "文件" / "基金名称映射.csv"


def load_master() -> tuple[pd.DataFrame, list[str], list[str], set[str]]:
    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    external_cols = list(set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"})
    fund_set = set(fund_cols)
    non_fund = {"Date"} | set(external_cols)
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    return master, fund_cols, external_cols, all_etfs


def corr_top_pairs(corr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            v = corr.loc[a, b]
            if not np.isfinite(v):
                continue
            group = "ETF-ETF" if (a in ETF_SET and b in ETF_SET) else ("EXT-EXT" if (a not in ETF_SET and b not in ETF_SET) else "ETF-EXT")
            rows.append({"pair_a": a, "pair_b": b, "corr": float(v), "abs_corr": abs(float(v)), "group": group})
    df = pd.DataFrame(rows).sort_values("abs_corr", ascending=False).reset_index(drop=True)
    return df


def unconditional_stats(master: pd.DataFrame, fund_cols: list[str]) -> pd.DataFrame:
    rows = []
    for t in fund_cols:
        s = master[t].to_numpy(dtype=float) * 100.0
        s = s[np.isfinite(s)]
        rows.append({
            "ticker": t,
            "n": int(s.size),
            "avg": float(s.mean()) if s.size else float("nan"),
            "hit": float((s > 0).mean()) if s.size else float("nan"),
            "std": float(s.std(ddof=1)) if s.size > 1 else float("nan"),
            "ann_vol": float(s.std(ddof=1) * np.sqrt(252)) if s.size > 1 else float("nan"),
            "downside_std": float(np.sqrt(np.mean(np.minimum(s, 0.0) ** 2))) if s.size else float("nan"),
            "avg_std": float(s.mean() / s.std(ddof=1)) if s.size > 1 and s.std(ddof=1) > 0 else float("nan"),
            "median": float(np.median(s)) if s.size else float("nan"),
            "p10": float(np.percentile(s, 10)) if s.size else float("nan"),
            "p90": float(np.percentile(s, 90)) if s.size else float("nan"),
            "max": float(s.max()) if s.size else float("nan"),
            "min": float(s.min()) if s.size else float("nan"),
        })
    return pd.DataFrame(rows)


def add_risk_flags(df: pd.DataFrame, uncond: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.merge(uncond[["ticker", "std", "avg_std"]], on="ticker", how="left", suffixes=("", "_uncond"))
    out["flag_std_high"] = (out["full_std"] > 1.5 * out["std"]).astype(int)
    out["flag_avgstd_low"] = (out["full_avg_std"] < 0.5 * out["avg_std"]).astype(int)
    out["flag_test_std_high"] = (out["test_std"] > 1.5 * out["train_std"]).astype(int)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    global ETF_SET
    master, fund_cols, external_cols, all_etfs = load_master()
    ETF_SET = set(all_etfs)
    etf_cols = sorted(all_etfs)
    factor_cols = etf_cols + external_cols

    print("correlation matrix...", flush=True)
    corr = master[factor_cols].corr(method="pearson")
    corr.to_csv(OUT_DIR / "v4_corr_matrix.csv", index_label="factor")
    top = corr_top_pairs(corr)
    top.to_csv(OUT_DIR / "v4_corr_top_pairs.csv", index=False)
    print("top pairs:", len(top), flush=True)

    print("fund-factor correlations...", flush=True)
    fund_factor = master[fund_cols + factor_cols].corr(method="pearson").loc[fund_cols, factor_cols]
    fund_factor.to_csv(OUT_DIR / "v4_fund_factor_corr.csv", index_label="ticker")

    print("unconditional fund stats...", flush=True)
    uncond = unconditional_stats(master, fund_cols)
    uncond.to_csv(OUT_DIR / "v4_fund_unconditional_stats.csv", index=False)

    print("risk by strategy...", flush=True)
    by_strategy = pd.read_csv(OUT_DIR / "v4_oos_fixed_split_by_strategy.csv")
    by_strategy = add_risk_flags(by_strategy, uncond)
    by_strategy.to_csv(OUT_DIR / "v4_risk_by_strategy.csv", index=False)

    merged = pd.read_csv(OUT_DIR / "v4_oos_fixed_split_merged.csv")
    merged = add_risk_flags(merged, uncond)
    merged.to_csv(OUT_DIR / "v4_risk_merged.csv", index=False)

    flags = pd.DataFrame({
        "dataset": ["by_strategy", "merged"],
        "flag_std_high": [int(by_strategy["flag_std_high"].sum()), int(merged["flag_std_high"].sum())],
        "flag_avgstd_low": [int(by_strategy["flag_avgstd_low"].sum()), int(merged["flag_avgstd_low"].sum())],
        "flag_test_std_high": [int(by_strategy["flag_test_std_high"].sum()), int(merged["flag_test_std_high"].sum())],
    })
    flags.to_csv(OUT_DIR / "v4_risk_flags.csv", index=False)
    print("saved all correlation/risk files")


if __name__ == "__main__":
    main()

