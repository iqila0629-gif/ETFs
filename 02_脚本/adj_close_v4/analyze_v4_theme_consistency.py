"""Compare strategy consistency within same-theme funds and safe-haven groups."""

from __future__ import annotations

import sys
import itertools

import pandas as pd

import config
from build_v4_strategy_explanation import parse_parts

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
SAFE_THEMES = {"贵金属", "公用事业", "必需消费", "国债", "利率机会"}


def tokenize_condition(condition: str) -> list[str]:
    return parse_parts(condition)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expl = pd.read_csv(OUT_DIR / "v4_strategy_explanation_v3.csv")
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv")
    df = mapping.merge(
        expl[["ticker", "strategy_no", "fund_name", "fund_theme"]],
        on=["ticker", "strategy_no"], how="left"
    )

    rows = []
    top_token_rows = []
    for theme, g in df.groupby("fund_theme", sort=True):
        tickers = sorted(g["ticker"].unique())
        token_counter: dict[str, int] = {}
        condition_counter: dict[str, int] = {}
        for _, r in g.iterrows():
            for tok in tokenize_condition(r["condition"]):
                token_counter[tok] = token_counter.get(tok, 0) + 1
            condition_counter[r["condition"]] = condition_counter.get(r["condition"], 0) + 1
        top_conditions = " | ".join(
            f"{k}x{c}" for k, c in sorted(condition_counter.items(), key=lambda x: -x[1])[:5]
        )
        top_tokens = " | ".join(
            f"{k}x{c}" for k, c in sorted(token_counter.items(), key=lambda x: -x[1])[:8]
        )
        rows.append({
            "theme": theme,
            "funds": len(tickers),
            "strategies": len(g),
            "avg_full_avg": float(g["full_avg"].mean()),
            "avg_full_hit": float(g["full_hit"].mean()),
            "median_full_avg": float(g["full_avg"].median()),
            "median_full_hit": float(g["full_hit"].median()),
            "top_conditions": top_conditions,
            "top_tokens": top_tokens,
        })
        for tok, cnt in sorted(token_counter.items(), key=lambda x: -x[1])[:10]:
            top_token_rows.append({"theme": theme, "token": tok, "count": cnt})
    pd.DataFrame(rows).to_csv(OUT_DIR / "v4_theme_summary.csv", index=False)
    pd.DataFrame(top_token_rows).to_csv(OUT_DIR / "v4_theme_top_tokens.csv", index=False)

    fund_tokens = {}
    fund_theme = {}
    for ticker, g in df.groupby("ticker"):
        tokens = set()
        for _, r in g.iterrows():
            tokens.update(tokenize_condition(r["condition"]))
        fund_tokens[ticker] = tokens
        fund_theme[ticker] = g["fund_theme"].iloc[0]

    def jaccard(a: set, b: set) -> float:
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    tickers = sorted(fund_tokens)
    within: dict[str, list[float]] = {}
    across: list[float] = []
    for a, b in itertools.combinations(tickers, 2):
        j = jaccard(fund_tokens[a], fund_tokens[b])
        if fund_theme[a] == fund_theme[b]:
            within.setdefault(fund_theme[a], []).append(j)
        else:
            across.append(j)
    sim_rows = []
    for theme in sorted(within):
        vals = within[theme]
        sim_rows.append({
            "theme": theme,
            "funds": sum(1 for t in tickers if fund_theme[t] == theme),
            "within_pairs": len(vals),
            "within_mean_jaccard": float(sum(vals) / len(vals)) if vals else float("nan"),
            "within_median_jaccard": float(sorted(vals)[len(vals) // 2]) if vals else float("nan"),
        })
    if across:
        baseline = float(sum(across) / len(across))
    else:
        baseline = float("nan")
    for r in sim_rows:
        r["across_mean_jaccard"] = baseline
    pd.DataFrame(sim_rows).to_csv(OUT_DIR / "v4_theme_similarity.csv", index=False)

    safe = df[df["fund_theme"].isin(SAFE_THEMES)].copy()
    safe.to_csv(OUT_DIR / "v4_theme_safe_haven.csv", index=False)
    print("theme summary:", len(rows), "safe haven strategies:", len(safe))
    print("baseline across-theme jaccard:", round(baseline, 4))


if __name__ == "__main__":
    main()


