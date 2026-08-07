"""v4 Phase 3: exhaustive triple-ETF scan over all funds (original 19 ETFs)."""

from __future__ import annotations

import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

import config


CUTOFF = np.datetime64("2025-01-01")
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
MIN_ABS_AVG = 0.2
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55
HORIZONS = [1, 2, 3]
DECISION_N = 100
DECISION_P = 0.52
DECISION_ABS = 0.15
RAW_EVENT_MIN = FULL_MIN + DECISION_N

PATTERNS = [
    ("up_up_up", (1, 1, 1)),
    ("down_down_down", (-1, -1, -1)),
    ("up_up_down", (1, 1, -1)),
    ("up_down_up", (1, -1, 1)),
    ("down_up_up", (-1, 1, 1)),
    ("down_down_up", (-1, -1, 1)),
    ("down_up_down", (-1, 1, -1)),
    ("up_down_down", (1, -1, -1)),
]


def fund_group(ticker: str) -> str:
    if ticker.endswith("SX"):
        return "inverse"
    if ticker.startswith("U"):
        return "ultra_long"
    return "long"


def load_master() -> tuple[pd.DataFrame, list[str], np.ndarray, np.ndarray]:
    panel_path = config.V4_ETF20_PANEL if config.V4_ETF20_PANEL.exists() else config.V4_ETF19_PANEL
    panel = pd.read_csv(panel_path)
    if "date" in panel.columns:
        panel = panel.rename(columns={"date": "Date"})
    external = pd.read_csv(config.V4_EXTERNAL_PANEL, parse_dates=["Date"])
    panel["Date"] = pd.to_datetime(panel["Date"])
    master = (
        panel.merge(external, on="Date", how="left")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    dates = master["Date"].to_numpy()
    fund_arr = master[fund_cols].to_numpy(dtype=float)
    return master, fund_cols, dates, fund_arr


def build_target(fund_arr: np.ndarray, horizon: int) -> np.ndarray:
    n, f = fund_arr.shape
    if horizon == 1:
        out = np.full((n, f), np.nan)
        out[:-1, :] = fund_arr[1:, :]
        return out * 100.0
    shifted = np.empty((n, f, horizon))
    for k in range(1, horizon + 1):
        shifted[:, :, k - 1] = np.roll(fund_arr, -k, axis=0)
    shifted[-horizon:, :, :] = np.nan
    valid = ~np.isnan(shifted).any(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = shifted.mean(axis=2)
    return np.where(valid, mean * 100.0, np.nan)


def evaluate_mask(
    mask: np.ndarray,
    target_col: np.ndarray,
    dates: np.ndarray,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    valid = mask & np.isfinite(target_col)
    idx = np.flatnonzero(valid)
    ev_dates = dates[idx]
    vals = target_col[idx]
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool)
    up = vals > 0
    down = vals < 0
    cum_n = np.arange(n, dtype=float)
    cum_up = np.concatenate([[0.0], np.cumsum(up)[:-1]])
    cum_down = np.concatenate([[0.0], np.cumsum(down)[:-1]])
    cum_su = np.concatenate([[0.0], np.cumsum(np.where(up, vals, 0.0))[:-1]])
    cum_sd = np.concatenate([[0.0], np.cumsum(np.where(down, vals, 0.0))[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_up = cum_up / cum_n
        p_down = cum_down / cum_n
        avg_up = cum_su / np.where(cum_up > 0, cum_up, 1)
        avg_down = cum_sd / np.where(cum_down > 0, cum_down, 1)
        dec_up = (cum_n >= min_n) & (p_up >= min_p) & (avg_up >= min_abs)
        dec_down = (cum_n >= min_n) & (p_down >= min_p) & (avg_down <= -min_abs)
    trade_mask = dec_up | dec_down
    return ev_dates, vals, trade_mask


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    master, fund_cols, dates, fund_arr = load_master()
    etf_cols = sorted(config.V4_UNIVERSE)
    targets = {h: build_target(fund_arr, h) for h in HORIZONS}
    all_tickers = fund_cols
    etf_data = {c: master[c].to_numpy(dtype=float) for c in etf_cols}

    combos = list(itertools.combinations(etf_cols, 3))
    total_conditions = len(combos) * len(PATTERNS) * len(HORIZONS)
    print(
        f"triples={len(combos)} patterns={len(PATTERNS)} horizons={HORIZONS} "
        f"condition-horizon combos={total_conditions} funds={len(all_tickers)}",
        flush=True,
    )

    summary_rows: list[dict] = []
    pass_rows: list[dict] = []
    checked = 0
    for pi, (a, b, c) in enumerate(combos):
        if limit is not None and pi >= limit:
            break
        A, B, C = etf_data[a], etf_data[b], etf_data[c]
        for pattern_name, (sa, sb, sc) in PATTERNS:
            mask = (
                ((A > 0) if sa == 1 else (A < 0))
                & ((B > 0) if sb == 1 else (B < 0))
                & ((C > 0) if sc == 1 else (C < 0))
            )
            def sw(s: int) -> str:
                return "up" if s == 1 else "down"

            condition = f"{a}_{sw(sa)}_{b}_{sw(sb)}_{c}_{sw(sc)}"
            for horizon in HORIZONS:
                target = targets[horizon]
                valid = mask[:, None] & np.isfinite(target)
                event_counts = valid.sum(axis=0)
                frozen_counts = (valid & (dates[:, None] >= CUTOFF)).sum(axis=0)
                eligible = np.flatnonzero(
                    (event_counts >= RAW_EVENT_MIN) & (frozen_counts >= FROZEN_MIN)
                )
                summary_rows.append(
                    {
                        "condition": condition,
                        "horizon": horizon,
                        "eligible_funds": int(eligible.size),
                        "pass_signals": 0,
                    }
                )
                for fi in eligible:
                    ticker = all_tickers[fi]
                    ev_dates, vals, trade_mask = evaluate_mask(
                        mask,
                        target[:, fi],
                        dates,
                        DECISION_N,
                        DECISION_P,
                        DECISION_ABS,
                    )
                    if not trade_mask.any():
                        continue
                    td = ev_dates[trade_mask]
                    tv = vals[trade_mask]
                    hold = td >= CUTOFF
                    full_avg = float(tv.mean())
                    full_trades = int(tv.size)
                    full_hit = float((tv > 0).mean())
                    frozen_avg = float(tv[hold].mean()) if hold.any() else float("nan")
                    frozen_trades = int(hold.sum())
                    frozen_hit = float((tv[hold] > 0).mean()) if hold.any() else float("nan")
                    if full_trades < FULL_MIN or frozen_trades < FROZEN_MIN:
                        continue
                    is_pass = bool(
                        abs(full_avg) >= MIN_ABS_AVG
                        and full_trades >= FULL_MIN
                        and full_hit > MIN_FULL_HIT
                        and frozen_avg == frozen_avg
                        and abs(frozen_avg) >= MIN_ABS_AVG
                        and frozen_trades >= FROZEN_MIN
                        and frozen_hit >= MIN_FROZEN_HIT
                    )
                    row = {
                        "ticker": ticker,
                        "fund_group": fund_group(ticker),
                        "source": "triple_scan",
                        "condition": condition,
                        "horizon": horizon,
                        "full_avg": full_avg,
                        "full_trades": full_trades,
                        "full_hit": full_hit,
                        "frozen_avg": frozen_avg,
                        "frozen_trades": frozen_trades,
                        "frozen_hit": frozen_hit,
                        "pass": is_pass,
                    }
                    if is_pass:
                        pass_rows.append(row)
                        summary_rows[-1]["pass_signals"] += 1
                checked += 1
        if (pi + 1) % 100 == 0:
            print(
                f"combos {pi + 1}/{len(combos)} checked={checked} "
                f"pass={len(pass_rows)}",
                flush=True,
            )

    stats_df = pd.DataFrame(summary_rows)
    pass_df = pd.DataFrame(pass_rows)
    stats_path = config.V4_TRIPLE_SCAN_STATS
    pass_path = config.V4_TRIPLE_PASS
    if len(stats_df):
        stats_df.to_csv(stats_path, index=False)
    if len(pass_df):
        pass_df.to_csv(pass_path, index=False)

    print(f"checked={checked} pass={len(pass_df)}")
    if len(pass_df):
        print("pass funds:", pass_df["ticker"].nunique())
        print("pass condition count:", pass_df["condition"].nunique())

    # Combine with the v4 baseline (original 19, recommended thresholds).
    baseline_path = config.V4_OUT / "v4_19etf_baseline_pass.csv"
    if baseline_path.exists() and len(pass_df):
        baseline = pd.read_csv(baseline_path, keep_default_na=False)
        baseline = baseline.drop(columns=["abs_full_avg"], errors="ignore")
        combined = pd.concat([baseline, pass_df], ignore_index=True)
        combined["abs_full_avg"] = pd.to_numeric(combined["full_avg"], errors="coerce").abs()
        combined = combined.sort_values(
            ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=False,
        )
        combined = combined.drop_duplicates(
            ["ticker", "condition", "horizon"], keep="first"
        )
        combined.to_csv(config.V4_OUT / "v4_phase3_combined_pass.csv", index=False)

        best = (
            combined.sort_values(
                ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
                ascending=False,
            )
            .groupby("ticker", sort=True)
            .head(1)
            .sort_values("ticker")
            .reset_index(drop=True)
        )
        best.to_csv(config.V4_OUT / "v4_phase3_best_strategy.csv", index=False)
        print(
            "combined pass signals:",
            len(combined),
            "funds:",
            combined["ticker"].nunique(),
        )
        print("phase3 best funds:", len(best))
    else:
        print("no triple pass rows to combine with baseline")


if __name__ == "__main__":
    main()
