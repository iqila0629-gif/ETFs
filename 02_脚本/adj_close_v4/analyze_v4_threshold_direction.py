"""Find funds whose bucket/streak direction deviates from the all-fund median direction."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
PANEL = config.EVENT_INPUTS / "panel_fund_returns_adj.csv"
MIN_BUCKET_N = 30
MIN_BUCKETS = 4
MIN_STREAK_N = 30


def clip_mean(vals: np.ndarray) -> float:
    vals = np.clip(vals, -50, 50)
    return float(vals.mean()) if vals.size else float("nan")


def bucket_stats(r: np.ndarray, target: np.ndarray, lo: float, hi: float) -> tuple[int, float]:
    if lo == -np.inf:
        keep = r <= hi
    elif hi == np.inf:
        keep = r > lo
    else:
        keep = (r > lo) & (r <= hi)
    v = target[keep & np.isfinite(target)]
    return int(v.size), clip_mean(v)


def streak_avg(r: np.ndarray, target: np.ndarray, n: int, direction: str) -> tuple[int, float]:
    mask = (r < 0) if direction == "down" else (r > 0)
    for k in range(1, n):
        mask = mask & (np.roll(r, k) < 0 if direction == "down" else np.roll(r, k) > 0)
    mask[: n - 1] = False
    v = target[mask & np.isfinite(target)]
    return int(v.size), clip_mean(v)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(PANEL)
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv")
    covered = set(mapping["ticker"])
    tickers = [c for c in panel.columns if c != "date" and c in covered]
    rows: list[dict] = []

    neg_edges = [-np.inf, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0]
    pos_edges = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, np.inf]

    for ticker in tickers:
        r = panel[ticker].to_numpy(dtype=float) * 100.0
        target = np.full(r.size, np.nan)
        target[:-1] = r[1:]

        # negative buckets: deeper drop should raise next-day avg (all-fund direction)
        neg = [bucket_stats(r, target, neg_edges[i], neg_edges[i + 1]) for i in range(len(neg_edges) - 1)]
        neg = [(n, a) for n, a in neg if n >= MIN_BUCKET_N]
        if len(neg) >= MIN_BUCKETS:
            depth = np.arange(1, len(neg) + 1, dtype=float)
            avg = np.array([a for _, a in neg], dtype=float)
            ok = np.isfinite(avg)
            if ok.sum() >= MIN_BUCKETS:
                rho = float(np.corrcoef(depth[ok], avg[ok])[0, 1])
                opposite = bool(rho < -0.5)
                if opposite:
                    rows.append({
                        "ticker": ticker,
                        "type": "负向分桶方向相反",
                        "detail": f"rho={rho:.2f}，最浅桶均值为{avg[ok][0]:.3f}%，最深桶均值为{avg[ok][-1]:.3f}%",
                    })

        # positive buckets: deeper rise should lower next-day avg (all-fund direction)
        pos = [bucket_stats(r, target, pos_edges[i], pos_edges[i + 1]) for i in range(len(pos_edges) - 1)]
        pos = [(n, a) for n, a in pos if n >= MIN_BUCKET_N]
        if len(pos) >= MIN_BUCKETS:
            depth = np.arange(1, len(pos) + 1, dtype=float)
            avg = np.array([a for _, a in pos], dtype=float)
            ok = np.isfinite(avg)
            if ok.sum() >= MIN_BUCKETS:
                rho = float(np.corrcoef(depth[ok], avg[ok])[0, 1])
                opposite = bool(rho > 0.5)
                if opposite:
                    rows.append({
                        "ticker": ticker,
                        "type": "正向分桶方向相反",
                        "detail": f"rho={rho:.2f}，最浅桶均值为{avg[ok][0]:.3f}%，最深桶均值为{avg[ok][-1]:.3f}%",
                    })

        # down streaks: longer streak should raise next-day avg
        down = [streak_avg(r, target, n, "down") for n in range(1, 6)]
        down = [(n, a) for n, a in down if n >= MIN_STREAK_N]
        if len(down) >= 3:
            depth = np.arange(1, len(down) + 1, dtype=float)
            avg = np.array([a for _, a in down], dtype=float)
            ok = np.isfinite(avg)
            if ok.sum() >= 3:
                rho = float(np.corrcoef(depth[ok], avg[ok])[0, 1])
                opposite = bool(rho < -0.5)
                if opposite:
                    rows.append({
                        "ticker": ticker,
                        "type": "连跌方向相反",
                        "detail": f"rho={rho:.2f}，1日连跌均值{avg[ok][0]:.3f}%，最长连跌均值{avg[ok][-1]:.3f}%",
                    })

        # up streaks: longer streak should lower next-day avg
        up = [streak_avg(r, target, n, "up") for n in range(1, 6)]
        up = [(n, a) for n, a in up if n >= MIN_STREAK_N]
        if len(up) >= 3:
            depth = np.arange(1, len(up) + 1, dtype=float)
            avg = np.array([a for _, a in up], dtype=float)
            ok = np.isfinite(avg)
            if ok.sum() >= 3:
                rho = float(np.corrcoef(depth[ok], avg[ok])[0, 1])
                opposite = bool(rho > 0.5)
                if opposite:
                    rows.append({
                        "ticker": ticker,
                        "type": "连涨方向相反",
                        "detail": f"rho={rho:.2f}，1日连涨均值{avg[ok][0]:.3f}%，最长连涨均值{avg[ok][-1]:.3f}%",
                    })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "v4_threshold_direction_deviation.csv", index=False)
    print("deviation rows:", len(df))
    print(df["type"].value_counts().to_string())
    print(df.head(40).to_string(index=False))


if __name__ == "__main__":
    main()


