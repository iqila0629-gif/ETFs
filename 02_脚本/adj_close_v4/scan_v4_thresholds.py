"""v4 threshold sensitivity scan on the original-19 ETF signal pool."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import config


CUTOFF = np.datetime64("2025-01-01")
MIN_ABS_AVG = 0.2
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55


def load_master() -> pd.DataFrame:
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
    return master


def build_condition_mask(
    master: pd.DataFrame,
    condition: str,
    ticker: str,
    all_etfs: set[str],
) -> pd.Series:
    if condition.startswith("ext_"):
        ext_map = {
            "ext_vix_chg_ge5": master["VIX_Chg%"] >= 5,
            "ext_vix_chg_le-5": master["VIX_Chg%"] <= -5,
            "ext_vix5d_ge10": master["VIX_5dChg"] >= 10,
            "ext_vix5d_le-10": master["VIX_5dChg"] <= -10,
            "ext_vix_ge25": master["VIX_Close"] >= 25,
            "ext_vix_le15": master["VIX_Close"] <= 15,
            "ext_tnx_bp_ge10": master["TNX_ChgBp"] >= 10,
            "ext_tnx_bp_le-10": master["TNX_ChgBp"] <= -10,
        }
        return ext_map[condition]
    if condition.startswith("self_"):
        r = master[ticker]
        name = condition.removeprefix("self_")
        if name == "up":
            return r > 0
        if name == "down":
            return r < 0
        if name == "big_up":
            return r >= 0.02
        if name == "big_down":
            return r <= -0.02
        if name == "3up":
            return (r > 0) & (r.shift(1) > 0) & (r.shift(2) > 0)
        if name == "3down":
            return (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0)
        raise ValueError(f"unknown self condition {condition}")

    tokens = condition.split("_")
    if len(tokens) == 4 and tokens[0] in all_etfs and tokens[2] in all_etfs:
        a, sa, b, sb = tokens
        ma = master[a] > 0 if sa == "up" else master[a] < 0
        mb = master[b] > 0 if sb == "up" else master[b] < 0
        return ma & mb
    if len(tokens) == 2 and tokens[0] in all_etfs:
        etf, suffix = tokens
        s = master[etf]
        if suffix == "up":
            return s > 0
        if suffix == "down":
            return s < 0
        if suffix == "big_up":
            return s >= 1.0
        if suffix == "big_down":
            return s <= -1.0
        if suffix == "gt2":
            return s > 2.0
        if suffix == "lt-2":
            return s < -2.0
    if len(tokens) >= 3 and tokens[0] in all_etfs and tokens[1] in {"big", "gt", "lt"}:
        etf = tokens[0]
        suffix = "_".join(tokens[1:])
        s = master[etf]
        if suffix == "big_up":
            return s >= 1.0
        if suffix == "big_down":
            return s <= -1.0
        if suffix == "gt2":
            return s > 2.0
        if suffix == "lt-2":
            return s < -2.0
    if len(tokens) >= 3 and tokens[0] in all_etfs and tokens[1] == "bin":
        etf = tokens[0]
        s = master[etf]
        band = "_".join(tokens[2:])
        if band == "gt2":
            return s > 2.0
        if band == "lt-2":
            return s < -2.0
        lo, hi = (float(x) for x in band.split("_"))
        if lo >= 0:
            return (s > lo) & (s <= hi)
        return (s >= lo) & (s < hi)
    raise ValueError(f"cannot parse condition {condition}")


def multi_day_target(
    master: pd.DataFrame,
    ticker: str,
    horizon: int,
    strict_finite: bool = False,
) -> np.ndarray:
    arr = master[ticker].to_numpy(dtype=float)
    n = arr.size
    if horizon == 1:
        out = np.full(n, np.nan)
        out[:-1] = arr[1:]
        return out
    shifted = np.column_stack([np.roll(arr, -k) for k in range(1, horizon + 1)])
    shifted[-horizon:, :] = np.nan
    if strict_finite:
        return np.mean(shifted, axis=1)
    count = np.sum(~np.isnan(shifted), axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        total = np.nansum(shifted, axis=1)
        mean = np.divide(total, count, out=np.full(n, np.nan), where=count > 0)
    return mean


def evaluate(
    mask: pd.Series,
    target: np.ndarray,
    dates: np.ndarray,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target)
    idx = np.flatnonzero(valid)
    ev_dates = dates[idx]
    vals = target[idx] * 100.0
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


def etf_tokens(condition: str, all_etfs: set[str]) -> list[str]:
    return [t for t in str(condition).split("_") if t in all_etfs]


def allowed_condition(condition: str, all_etfs: set[str]) -> bool:
    return set(etf_tokens(condition, all_etfs)) <= config.ORIGINAL19


def load_pool(all_etfs: set[str]) -> pd.DataFrame:
    v3 = pd.read_csv(config.V3_PASS, keep_default_na=False)
    pair = pd.read_csv(config.PAIR_STRICT, keep_default_na=False)
    cols = [
        "ticker",
        "fund_group",
        "source",
        "condition",
        "horizon",
        "full_avg",
        "full_trades",
        "full_hit",
        "frozen_avg",
        "frozen_trades",
        "frozen_hit",
    ]
    pool = pd.concat([v3[cols], pair[cols]], ignore_index=True)
    all_known_etf_tokens = {
        t
        for c in pool["condition"]
        for t in str(c).split("_")
        if t.isupper() and len(t) in (3, 4)
    }
    pool = pool[
        pool["condition"].apply(
            lambda c: set(etf_tokens(c, all_known_etf_tokens)) <= config.ORIGINAL19
        )
    ]
    for col in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")
    pool["abs_full_avg"] = pool["full_avg"].abs()
    pool = pool.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
        ascending=False,
    )
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    return pool.reset_index(drop=True)


def params_for(source: str) -> tuple[int, float, float]:
    return (100, 0.55, 0.2) if source == "main" else (100, 0.52, 0.15)


def recompute_stats(master: pd.DataFrame, pool: pd.DataFrame, dates: np.ndarray, all_etfs: set[str]) -> pd.DataFrame:
    mask_cache: dict[tuple[str, str | None], pd.Series] = {}
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    rows: list[dict] = []

    def get_mask(condition: str, ticker: str) -> pd.Series:
        key = (condition, ticker if condition.startswith("self_") else None)
        if key not in mask_cache:
            mask_cache[key] = build_condition_mask(master, condition, ticker, all_etfs)
        return mask_cache[key]

    def get_target(ticker: str, horizon: int, strict: bool) -> np.ndarray:
        key = (ticker, horizon, strict)
        if key not in target_cache:
            target_cache[key] = multi_day_target(master, ticker, horizon, strict)
        return target_cache[key]

    for i, row in enumerate(pool.itertuples(index=False), start=1):
        ticker = str(row.ticker)
        condition = str(row.condition)
        horizon = int(row.horizon)
        source = str(row.source)
        mask = get_mask(condition, ticker)
        target = get_target(ticker, horizon, strict=source == "pair_scan")
        ev_dates, vals, trade_mask = evaluate(mask, target, dates, *params_for(source))
        if not trade_mask.any():
            continue
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        hold = td >= CUTOFF
        rows.append(
            {
                "ticker": ticker,
                "fund_group": row.fund_group,
                "source": source,
                "condition": condition,
                "horizon": horizon,
                "full_avg": float(tv.mean()),
                "full_trades": int(tv.size),
                "full_hit": float((tv > 0).mean()),
                "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
                "frozen_trades": int(hold.sum()),
                "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan"),
            }
        )
        if i % 500 == 0:
            print(f"recomputed {i}/{len(pool)}", flush=True)
    return pd.DataFrame(rows)


def pass_flags(df: pd.DataFrame, full_min: int, frozen_min: int) -> pd.Series:
    return (
        df["full_avg"].abs().ge(MIN_ABS_AVG)
        & df["full_trades"].ge(full_min)
        & df["full_hit"].gt(MIN_FULL_HIT)
        & df["frozen_avg"].abs().ge(MIN_ABS_AVG)
        & df["frozen_trades"].ge(frozen_min)
        & df["frozen_hit"].ge(MIN_FROZEN_HIT)
    )


def best_per_fund(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["abs_full_avg"] = df["full_avg"].abs()
    return (
        df.sort_values(
            ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=False,
        )
        .groupby("ticker", sort=True)
        .head(1)
        .sort_values("ticker")
        .reset_index(drop=True)
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    master = load_master()
    fund_cols = set(pd.read_csv(config.FUND_PANEL).columns[1:])
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_cols and c not in non_fund}
    dates = master["Date"].to_numpy()
    all_tickers = sorted(fund_cols)

    print("loading and filtering candidate pool", flush=True)
    pool = load_pool(all_etfs)
    print("pool rows after original19 filter:", len(pool), "funds", pool["ticker"].nunique(), flush=True)

    print("recomputing walk-forward stats", flush=True)
    recomputed = recompute_stats(master, pool, dates, all_etfs)
    recomputed.to_csv(config.V4_OUT / "v4_19etf_recomputed_stats.csv", index=False)
    print("recomputed rows:", len(recomputed), flush=True)

    sensitivity_rows = []
    for full_min in config.THRESHOLD_GRID_FULL:
        for frozen_min in config.THRESHOLD_GRID_FROZEN:
            ok = recomputed[pass_flags(recomputed, full_min, frozen_min)]
            best = best_per_fund(ok)
            covered = set(best["ticker"])
            uncovered_non_money = sorted(
                t for t in all_tickers if t not in covered and t not in config.MONEY_FUNDS
            )
            row = {
                "full_min_trades": full_min,
                "frozen_min_trades": frozen_min,
                "signals": len(ok),
                "covered_funds": len(covered),
                "uncovered_non_money": len(uncovered_non_money),
                "uncovered_list": "|".join(uncovered_non_money),
            }
            if len(best):
                row.update(
                    {
                        "median_full_avg_abs": float(best["full_avg"].abs().median()),
                        "median_full_hit": float(best["full_hit"].median()),
                        "median_full_trades": int(best["full_trades"].median()),
                        "median_frozen_avg_abs": float(best["frozen_avg"].abs().median()),
                        "median_frozen_hit": float(best["frozen_hit"].median()),
                        "median_frozen_trades": int(best["frozen_trades"].median()),
                    }
                )
            else:
                row.update(
                    {
                        "median_full_avg_abs": "",
                        "median_full_hit": "",
                        "median_full_trades": "",
                        "median_frozen_avg_abs": "",
                        "median_frozen_hit": "",
                        "median_frozen_trades": "",
                    }
                )
            sensitivity_rows.append(row)
            print(f"full>={full_min} frozen>={frozen_min}: signals={len(ok)} covered={len(covered)}", flush=True)

    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(config.V4_OUT / "v4_threshold_sensitivity.csv", index=False)

    rec_full = config.RECOMMENDED_FULL_TRADES
    rec_frozen = config.RECOMMENDED_FROZEN_TRADES
    rec_ok = recomputed[pass_flags(recomputed, rec_full, rec_frozen)].copy()
    rec_ok["abs_full_avg"] = rec_ok["full_avg"].abs()
    rec_ok = rec_ok.sort_values(["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"], ascending=False)
    rec_ok.to_csv(config.V4_OUT / "v4_19etf_baseline_pass.csv", index=False)
    best_rec = best_per_fund(rec_ok)
    best_rec.to_csv(config.V4_OUT / "v4_19etf_best_strategy.csv", index=False)
    print(f"recommended {rec_full}/{rec_frozen}: signals={len(rec_ok)} funds={best_rec['ticker'].nunique() if len(best_rec) else 0}")
    print("saved sensitivity and baseline files")


if __name__ == "__main__":
    main()
