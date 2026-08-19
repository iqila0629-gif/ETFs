"""Strategy-level monotonicity deviation: flag groups whose avg/hit deviate from monotonic increase."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
DEVIATION_CUTOFF = 3


def direction_of(token: str) -> str:
    if token.endswith("down") or token.endswith("lt-2"):
        return "down"
    if token.endswith("up") or token.endswith("gt2"):
        return "up"
    if "down" in token:
        return "down"
    return "up"


def drop_positions(vals: np.ndarray) -> list[int]:
    return [int(i + 1) for i in range(len(vals) - 1) if vals[i + 1] < vals[i]]


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
        g = g.dropna(subset=["full_avg"]).sort_values("threshold")
        if len(g) < 2:
            continue
        avg = g["full_avg"].to_numpy(dtype=float)
        hit = g["full_hit"].to_numpy(dtype=float)
        avg_drops = int(np.sum(np.diff(avg) < 0))
        hit_drops = int(np.sum(np.diff(hit) < 0))
        rho_avg = float(np.corrcoef(np.arange(len(avg)), avg)[0, 1]) if len(avg) > 1 else float("nan")
        rho_hit = float(np.corrcoef(np.arange(len(hit)), hit)[0, 1]) if len(hit) > 1 else float("nan")
        groups.append({
            "ticker": tick,
            "condition": cond,
            "scan_token": tok,
            "horizon": h,
            "direction": direction_of(tok),
            "rho_avg": rho_avg,
            "rho_hit": rho_hit,
            "n_valid": len(avg),
            "avg_drops": avg_drops,
            "hit_drops": hit_drops,
            "total_drops": avg_drops + hit_drops,
            "max_drops": max(avg_drops, hit_drops),
            "avg_drop_pos": "|".join(str(x) for x in drop_positions(avg)),
            "hit_drop_pos": "|".join(str(x) for x in drop_positions(hit)),
        })
    df = pd.DataFrame(groups)

    flagged = df[df["max_drops"] >= DEVIATION_CUTOFF].copy()
    flagged["condition_text"] = flagged.apply(
        lambda r: cond_text.get((r["ticker"], r["condition"]), r["condition"]), axis=1
    )
    flagged["flag"] = flagged.apply(
        lambda r: "、".join(p for p, b in [("平均回报", r["avg_drops"] >= DEVIATION_CUTOFF), ("命中率", r["hit_drops"] >= DEVIATION_CUTOFF)] if b),
        axis=1,
    )
    flagged = flagged[["ticker", "condition", "condition_text", "scan_token", "horizon", "direction",
                       "rho_avg", "rho_hit", "n_valid", "avg_drops", "hit_drops", "total_drops", "max_drops",
                       "avg_drop_pos", "hit_drop_pos", "flag"]]
    flagged.to_csv(OUT_DIR / "v4_strategy_direction_deviation.csv", index=False)

    sensitivity = []
    for c in range(1, 7):
        sensitivity.append({
            "cutoff": c,
            "flagged_max": int((df["max_drops"] >= c).sum()),
            "flagged_total": int((df["total_drops"] >= c).sum()),
            "pct_max": round((df["max_drops"] >= c).mean() * 100, 2),
            "pct_total": round((df["total_drops"] >= c).mean() * 100, 2),
        })
    pd.DataFrame(sensitivity).to_csv(OUT_DIR / "v4_strategy_direction_sensitivity.csv", index=False)

    detail_cols = ["ticker", "condition_text", "scan_token", "horizon", "threshold", "full_avg", "full_hit", "full_trades"]
    keys = set(zip(flagged["ticker"], flagged["condition"], flagged["scan_token"], flagged["horizon"]))
    detail = []
    for (tick, cond, tok, h), g in sweep.groupby(["ticker", "condition", "scan_token", "horizon"]):
        if (tick, cond, tok, h) not in keys:
            continue
        ctext = cond_text.get((tick, cond), cond)
        for _, row in g.sort_values("threshold").iterrows():
            detail.append({
                "ticker": tick,
                "condition_text": ctext,
                "scan_token": tok,
                "horizon": h,
                "threshold": row["threshold"],
                "full_avg": row["full_avg"],
                "full_hit": row["full_hit"],
                "full_trades": row["full_trades"],
            })
    pd.DataFrame(detail).to_csv(OUT_DIR / "v4_strategy_direction_detail_v2.csv", index=False)

    print("groups:", len(df))
    print("flagged (max_drops>=", DEVIATION_CUTOFF, "):", len(flagged))
    print(flagged[["ticker", "scan_token", "avg_drops", "hit_drops", "max_drops", "flag"]].head(20).to_string(index=False))
    print("sensitivity:")
    print(pd.DataFrame(sensitivity).to_string(index=False))


if __name__ == "__main__":
    main()
