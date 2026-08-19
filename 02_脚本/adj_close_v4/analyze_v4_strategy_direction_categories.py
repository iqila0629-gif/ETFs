"""Classify abnormal threshold strategies and export multi-sheet Excel."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def classify(series: np.ndarray, n_valid: int) -> str:
    if n_valid < 4:
        return "触发阈值太少"
    s = np.asarray(series, dtype=float)
    if s.size < 3:
        return "触发阈值太少"
    # 末端反转：最后 1-2 个点明显低于前面的峰值，且尾部不再上升
    prefix_max = s[:-2].max() if s.size >= 3 else s[0]
    if min(s[-2:]) < prefix_max - 0.05 and s[-1] <= s[-2] + 0.05:
        return "末端反转"
    diffs = np.diff(s)
    sign_changes = int(np.sum(np.sign(diffs[1:]) != np.sign(diffs[:-1])))
    if sign_changes >= max(1, (s.size - 2) * 0.5):
        return "忽上忽下"
    peak_idx = int(np.argmax(s))
    if 0 < peak_idx < s.size - 1:
        return "拐点与整体不同"
    return "整体反向单调"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dev = pd.read_csv(OUT_DIR / "v4_strategy_direction_deviation.csv")
    sweep = pd.read_csv(OUT_DIR / "v4_threshold_monotonic.csv")

    rows = []
    for r in dev.itertuples(index=False):
        g = sweep[
            (sweep["ticker"] == r.ticker)
            & (sweep["condition"] == r.condition)
            & (sweep["scan_token"] == r.scan_token)
            & (sweep["horizon"] == r.horizon)
        ].sort_values("threshold")
        valid = g.dropna(subset=["full_avg"])
        avgs = valid["full_avg"].to_numpy(dtype=float)
        hits = valid["full_hit"].to_numpy(dtype=float)
        trades = valid["full_trades"].to_numpy(dtype=float)
        cat = classify(avgs, len(avgs))
        rows.append({
            "ticker": r.ticker,
            "condition": r.condition,
            "condition_text": r.condition_text,
            "scan_token": r.scan_token,
            "horizon": r.horizon,
            "direction": r.direction,
            "rho_avg": r.rho_avg,
            "rho_hit": r.rho_hit,
            "flag": r.flag,
            "category": cat,
            "avg_mono": bool(np.all(np.diff(avgs) >= 0)) if len(avgs) >= 2 else False,
            "n_valid_thresholds": len(avgs),
            "avg_min": float(avgs.min()) if len(avgs) else float("nan"),
            "avg_max": float(avgs.max()) if len(avgs) else float("nan"),
            "avg_last": float(avgs[-1]) if len(avgs) else float("nan"),
            "hit_min": float(hits.min()) if len(hits) else float("nan"),
            "hit_max": float(hits.max()) if len(hits) else float("nan"),
            "hit_last": float(hits[-1]) if len(hits) else float("nan"),
            "trades_min": float(trades.min()) if len(trades) else float("nan"),
            "trades_max": float(trades.max()) if len(trades) else float("nan"),
            "trades_last": float(trades[-1]) if len(trades) else float("nan"),
        })
    df = pd.DataFrame(rows)
    removed = df[(df["category"] == "触发阈值太少") & df["avg_mono"]].copy()
    df = df[~((df["category"] == "触发阈值太少") & df["avg_mono"])].copy()
    summary = df["category"].value_counts().rename_axis("category").reset_index(name="count")
    summary["pct"] = (summary["count"] / len(df) * 100).round(2)
    summary.to_csv(OUT_DIR / "v4_strategy_direction_category_summary.csv", index=False)
    df.to_csv(OUT_DIR / "v4_strategy_direction_category_rows.csv", index=False)

    # Detail rows in the same layout as v4_strategy_direction_detail_v2.csv
    detail_cols = ["ticker", "condition_text", "scan_token", "horizon", "threshold", "full_avg", "full_hit", "full_trades", "异常指标"]
    keys = set(zip(df["ticker"], df["condition"], df["scan_token"], df["horizon"]))
    cat_map = {}
    flag_map = {}
    for r in df.itertuples(index=False):
        key = (r.ticker, r.condition, r.scan_token, r.horizon)
        cat_map[key] = r.category
        flag_map[key] = r.flag
    removed_keys = set(zip(removed["ticker"], removed["condition"], removed["scan_token"], removed["horizon"]))
    removed_flag = {}
    for r in removed.itertuples(index=False):
        removed_flag[(r.ticker, r.condition, r.scan_token, r.horizon)] = r.flag

    def detail_for(group_df, keys_set, flag_map_use):
        out = []
        for (tick, cond, tok, h), g in group_df.groupby(["ticker", "condition", "scan_token", "horizon"]):
            if (tick, cond, tok, h) not in keys_set:
                continue
            cond_text = dev.loc[(dev["ticker"] == tick) & (dev["condition"] == cond) & (dev["scan_token"] == tok) & (dev["horizon"] == h), "condition_text"].iloc[0]
            for _, row in g.sort_values("threshold").iterrows():
                out.append({
                    "ticker": tick,
                    "condition": cond,
                    "condition_text": cond_text,
                    "scan_token": tok,
                    "horizon": h,
                    "threshold": row["threshold"],
                    "full_avg": row["full_avg"],
                    "full_hit": row["full_hit"],
                    "full_trades": row["full_trades"],
                    "异常指标": flag_map_use[(tick, cond, tok, h)],
                })
        return out

    detail_df = pd.DataFrame(detail_for(sweep, keys, flag_map))
    detail_df["_category"] = detail_df.apply(lambda r: cat_map[(r["ticker"], r["condition"], r["scan_token"], r["horizon"])], axis=1)
    removed_detail_df = pd.DataFrame(detail_for(sweep, removed_keys, removed_flag))

    xlsx_path = OUT_DIR / "v4_strategy_direction_categories.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        detail_df[detail_cols].to_excel(writer, sheet_name="汇总", index=False)
        for cat in sorted(detail_df["_category"].unique()):
            detail_df[detail_df["_category"] == cat][detail_cols].to_excel(writer, sheet_name=cat, index=False)
        if not removed_detail_df.empty:
            removed_detail_df[detail_cols].to_excel(writer, sheet_name="已剔除_触发阈值太少_正向单调", index=False)
    print("classified rows:", len(df))
    print(summary.to_string(index=False))
    print("xlsx:", xlsx_path)


if __name__ == "__main__":
    main()






