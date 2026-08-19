"""Classify monotonicity-deviation anomalies by deviation count and position."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def classify_series(avg: np.ndarray, hit: np.ndarray, n_valid: int) -> str:
    if n_valid < 4:
        return "触发阈值太少"
    s = np.asarray(avg, dtype=float)
    h = np.asarray(hit, dtype=float)
    n = len(s)
    if n < 3:
        return "触发阈值太少"

    avg_drops = int(np.sum(np.diff(s) < 0))
    hit_drops = int(np.sum(np.diff(h) < 0))
    max_drops = max(avg_drops, hit_drops)
    if max_drops >= n - 1:
        return "反向单调"

    peak = int(np.argmax(s))
    avg_drop_pos = [int(i + 1) for i in range(n - 1) if s[i + 1] < s[i]]
    hit_drop_pos = [int(i + 1) for i in range(n - 1) if h[i + 1] < h[i]]
    tail = {n - 2, n - 1}
    if all(p in tail for p in avg_drop_pos + hit_drop_pos) and peak >= n - 2:
        return "末端反转"

    if 1 <= peak <= n - 2 and len([p for p in avg_drop_pos if p > peak]) >= 2:
        return "拐点"

    def sign_changes(x: np.ndarray) -> int:
        d = np.sign(np.diff(x))
        return int(np.sum(d[1:] != d[:-1]))

    if sign_changes(s) >= max(1, (n - 2) // 2) or sign_changes(h) >= max(1, (n - 2) // 2):
        return "忽上忽下"

    return "部分偏离"


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
        ].dropna(subset=["full_avg"]).sort_values("threshold")
        avg = g["full_avg"].to_numpy(dtype=float)
        hit = g["full_hit"].to_numpy(dtype=float)
        cat = classify_series(avg, hit, len(avg))
        rows.append({
            "ticker": r.ticker,
            "condition": r.condition,
            "condition_text": r.condition_text,
            "scan_token": r.scan_token,
            "horizon": r.horizon,
            "direction": r.direction,
            "rho_avg": r.rho_avg,
            "rho_hit": r.rho_hit,
            "n_valid": r.n_valid,
            "avg_drops": r.avg_drops,
            "hit_drops": r.hit_drops,
            "max_drops": r.max_drops,
            "avg_drop_pos": r.avg_drop_pos,
            "hit_drop_pos": r.hit_drop_pos,
            "flag": r.flag,
            "category": cat,
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "v4_strategy_direction_category_rows.csv", index=False)
    summary = df["category"].value_counts().rename_axis("category").reset_index(name="count")
    summary["pct"] = (summary["count"] / len(df) * 100).round(2)
    summary.to_csv(OUT_DIR / "v4_strategy_direction_category_summary.csv", index=False)

    detail_cols = ["ticker", "condition_text", "scan_token", "horizon", "threshold", "full_avg", "full_hit", "full_trades", "异常指标"]
    keys = set(zip(df["ticker"], df["condition"], df["scan_token"], df["horizon"]))
    flag_map = {}
    for r in df.itertuples(index=False):
        flag_map[(r.ticker, r.condition, r.scan_token, r.horizon)] = r.flag
    detail = []
    for (tick, cond, tok, h), g in sweep.groupby(["ticker", "condition", "scan_token", "horizon"]):
        if (tick, cond, tok, h) not in keys:
            continue
        ctext = dev.loc[(dev["ticker"] == tick) & (dev["condition"] == cond) & (dev["scan_token"] == tok) & (dev["horizon"] == h), "condition_text"].iloc[0]
        for _, row in g.sort_values("threshold").iterrows():
            detail.append({
                "ticker": tick,
                "condition": cond,
                "condition_text": ctext,
                "scan_token": tok,
                "horizon": h,
                "threshold": row["threshold"],
                "full_avg": row["full_avg"],
                "full_hit": row["full_hit"],
                "full_trades": row["full_trades"],
                "异常指标": flag_map[(tick, cond, tok, h)],
            })
    detail_df = pd.DataFrame(detail)
    detail_df["_category"] = detail_df.apply(lambda r: df.loc[(df["ticker"] == r["ticker"]) & (df["condition"] == r["condition"]) & (df["scan_token"] == r["scan_token"]) & (df["horizon"] == r["horizon"]), "category"].iloc[0], axis=1)

    xlsx_path = OUT_DIR / "v4_strategy_direction_categories.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        detail_df[detail_cols].to_excel(writer, sheet_name="汇总", index=False)
        for cat in sorted(detail_df["_category"].unique()):
            detail_df[detail_df["_category"] == cat][detail_cols].to_excel(writer, sheet_name=cat, index=False)

    print("classified rows:", len(df))
    print(summary.to_string(index=False))
    print("xlsx:", xlsx_path)


if __name__ == "__main__":
    main()
