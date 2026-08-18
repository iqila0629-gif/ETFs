"""Strategy-level threshold direction deviation vs all-strategy median direction."""

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
        y = g["full_avg"].to_numpy(dtype=float)
        rho = float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 and np.std(y) > 0 else float("nan")
        groups.append({
            "ticker": tick,
            "condition": cond,
            "scan_token": tok,
            "horizon": h,
            "direction": direction_of(tok),
            "rho": rho,
            "n_thresholds": len(g),
            "full_avg_delivered": float(g.iloc[0]["full_avg"]),
            "full_avg_deepest": float(g.iloc[-1]["full_avg"]),
        })
    df = pd.DataFrame(groups)
    med = df.groupby("direction")["rho"].median()
    df["median_rho"] = df["direction"].map(med)

    flagged = []
    for r in df.itertuples(index=False):
        if not np.isfinite(r.rho):
            continue
        if r.direction == "down":
            opposite = bool(r.median_rho > 0 and r.rho < -0.5)
        else:
            opposite = bool(r.median_rho < 0 and r.rho > 0.5)
        if opposite:
            flagged.append({
                "ticker": r.ticker,
                "condition": r.condition,
                "condition_text": cond_text.get((r.ticker, r.condition), r.condition),
                "scan_token": r.scan_token,
                "horizon": r.horizon,
                "direction": r.direction,
                "rho": r.rho,
                "median_rho": r.median_rho,
                "n_thresholds": r.n_thresholds,
                "full_avg_delivered": r.full_avg_delivered,
                "full_avg_deepest": r.full_avg_deepest,
            })
    fdf = pd.DataFrame(flagged)
    fdf.to_csv(OUT_DIR / "v4_strategy_direction_deviation.csv", index=False)


    print("groups:", len(df))
    print(med.to_string())
    print("flagged:", len(fdf))
    print(fdf.to_string(index=False) if len(fdf) else "")


if __name__ == "__main__":
    main()



