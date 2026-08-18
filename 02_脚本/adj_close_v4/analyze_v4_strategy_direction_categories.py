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
        return "拐点先升后降"
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
            "condition_text": r.condition_text,
            "scan_token": r.scan_token,
            "horizon": r.horizon,
            "direction": r.direction,
            "rho_avg": r.rho_avg,
            "rho_hit": r.rho_hit,
            "flag": r.flag,
            "category": cat,
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
    summary = df["category"].value_counts().rename_axis("category").reset_index(name="count")
    summary["pct"] = (summary["count"] / len(df) * 100).round(2)
    summary.to_csv(OUT_DIR / "v4_strategy_direction_category_summary.csv", index=False)

    xlsx_path = OUT_DIR / "v4_strategy_direction_categories.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="汇总", index=False)
        for cat in sorted(df["category"].unique()):
            df[df["category"] == cat].to_excel(writer, sheet_name=cat, index=False)
    print("classified rows:", len(df))
    print(summary.to_string(index=False))
    print("xlsx:", xlsx_path)


if __name__ == "__main__":
    main()
