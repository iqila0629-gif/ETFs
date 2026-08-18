"""Strategy-level threshold direction deviation vs all-strategy median direction (avg + hit)."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def direction_of(token: str) -> str:
    if token.endswith("down") or token.endswith("lt-2"):
        return "down"
    if token.endswith("up") or token.endswith("gt2"):
        return "up"
    if "down" in token:
        return "down"
    return "up"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sweep = pd.read_csv(OUT_DIR / "v4_threshold_monotonic.csv")
    expl = pd.read_csv(OUT_DIR / "v4_strategy_explanation_v3.csv")
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv")
    cond_map = mapping[["ticker", "strategy_no", "condition"]].merge(
        expl[["ticker", "strategy_no", "触发条件"]], on=["ticker", "strategy_no"], how="left"
    )
    cond_text = {}
    for _, r in cond_map.iterrows():
        cond_text[(r["ticker"], r["condition"])] = r["触发条件"]

    groups = []
    for (tick, cond, tok, h), g in sweep.groupby(["ticker", "condition", "scan_token", "horizon"]):
        g = g.dropna(subset=["full_avg"])
        if len(g) < 2:
            continue
        g = g.sort_values("threshold")
        x = g["threshold"].to_numpy(dtype=float)
        y_avg = g["full_avg"].to_numpy(dtype=float)
        y_hit = g["full_hit"].to_numpy(dtype=float)
        rho_avg = float(np.corrcoef(x, y_avg)[0, 1]) if np.std(x) > 0 and np.std(y_avg) > 0 else float("nan")
        rho_hit = float(np.corrcoef(x, y_hit)[0, 1]) if np.std(x) > 0 and np.std(y_hit) > 0 else float("nan")
        groups.append({
            "ticker": tick,
            "condition": cond,
            "scan_token": tok,
            "horizon": h,
            "direction": direction_of(tok),
            "rho_avg": rho_avg,
            "rho_hit": rho_hit,
            "n_thresholds": len(g),
            "full_avg_delivered": float(g.iloc[0]["full_avg"]),
            "full_avg_deepest": float(g.iloc[-1]["full_avg"]),
            "full_hit_delivered": float(g.iloc[0]["full_hit"]),
            "full_hit_deepest": float(g.iloc[-1]["full_hit"]),
        })
    df = pd.DataFrame(groups)
    med_avg = df.groupby("direction")["rho_avg"].median()
    med_hit = df.groupby("direction")["rho_hit"].median()
    df["median_rho_avg"] = df["direction"].map(med_avg)
    df["median_rho_hit"] = df["direction"].map(med_hit)

    flagged = []
    for r in df.itertuples(index=False):
        if not np.isfinite(r.rho_avg) and not np.isfinite(r.rho_hit):
            continue
        rho_avg = r.rho_avg if np.isfinite(r.rho_avg) else float("nan")
        rho_hit = r.rho_hit if np.isfinite(r.rho_hit) else float("nan")
        bad_avg = bool(np.isfinite(rho_avg) and rho_avg < -0.5)
        bad_hit = bool(np.isfinite(rho_hit) and rho_hit < -0.5)
        if bad_avg or bad_hit:
            flagged.append({
                "ticker": r.ticker,
                "condition": r.condition,
                "condition_text": cond_text.get((r.ticker, r.condition), r.condition),
                "scan_token": r.scan_token,
                "horizon": r.horizon,
                "direction": r.direction,
                "rho_avg": rho_avg,
                "rho_hit": rho_hit,
                "median_rho_avg": r.median_rho_avg,
                "median_rho_hit": r.median_rho_hit,
                "flag": "、".join(p for p, b in [("平均回报", bad_avg), ("命中率", bad_hit)] if b),
            })
    fdf = pd.DataFrame(flagged)
    fdf.to_csv(OUT_DIR / "v4_strategy_direction_deviation.csv", index=False)

    if len(fdf) >= 10:
        detail = []
        keys = set(zip(fdf["ticker"], fdf["condition"], fdf["scan_token"], fdf["horizon"]))
        for (tick, cond, tok, h), g in sweep.groupby(["ticker", "condition", "scan_token", "horizon"]):
            if (tick, cond, tok, h) not in keys:
                continue
            for _, row in g.iterrows():
                detail.append({
                    "ticker": tick,
                    "condition_text": cond_text.get((tick, cond), cond),
                    "scan_token": tok,
                    "horizon": h,
                    "threshold": row["threshold"],
                    "full_avg": row["full_avg"],
                    "full_hit": row["full_hit"],
                    "full_trades": row["full_trades"],
                })
        pd.DataFrame(detail).to_csv(OUT_DIR / "v4_strategy_direction_detail_v2.csv", index=False)
    print("groups:", len(df))
    print("median rho_avg:", med_avg.to_dict())
    print("median rho_hit:", med_hit.to_dict())
    print("flagged:", len(fdf))
    print(fdf.to_string(index=False) if len(fdf) else "")


if __name__ == "__main__":
    main()


