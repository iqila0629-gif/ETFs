"""Phase 9: dual-criteria (full history + frozen) rescreening and final outputs."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

import event_metrics as em
import walk_forward as wf
from generate_predictions import write_standard_csv


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "analysis_results" / "event_study"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
ETF19 = OUT_DIR / "panel_etf_returns.csv"
EXT_COMBINED = ROOT / "processed_returns" / "combined_extended_etf_returns.csv"
EXTERNAL_DAILY = OUT_DIR / "external_daily.csv"
STABLE = OUT_DIR / "stable_combos.csv"
SPARSE_BOSS = OUT_DIR / "boss_criterion_full_history_pass.csv"
OPT_SCAN = OUT_DIR / "optimization_scan.csv"

CANDIDATES = OUT_DIR / "dual_criteria_candidates.csv"
SUMMARY = OUT_DIR / "dual_criteria_summary.csv"
FIT_MATRIX = OUT_DIR / "fund_etf_fit_matrix.csv"
ETF_EFFECT = OUT_DIR / "etf_effectiveness.csv"
FULL_OUT = OUT_DIR / "final_outputs_dual_full_history"
FROZEN_OUT = OUT_DIR / "final_outputs_dual_frozen"

CUTOFF = np.datetime64("2025-01-01")
MONEY = {"MPIXX", "MPSXX"}


def multi_day_target(series: pd.Series, n: int) -> pd.Series:
    return pd.concat([series.shift(-k) for k in range(1, n + 1)], axis=1).mean(axis=1)


TARGET_CACHE: dict[tuple[str, int], pd.Series] = {}


def get_target(master: pd.DataFrame, ticker: str, horizon: int) -> pd.Series:
    key = (ticker, horizon)
    if key not in TARGET_CACHE:
        TARGET_CACHE[key] = multi_day_target(master[ticker], horizon)
    return TARGET_CACHE[key]


def evaluate(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target.to_numpy(dtype=float))
    ev_dates = dates.to_numpy()[valid]
    vals = target.to_numpy(dtype=float)[valid] * 100.0
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool), np.array([], dtype="U11")
    up_flag = vals > 0
    down_flag = vals < 0
    cum_n = np.arange(n, dtype=float)
    cum_up = np.concatenate([[0.0], np.cumsum(up_flag)[:-1]])
    cum_down = np.concatenate([[0.0], np.cumsum(down_flag)[:-1]])
    cum_su = np.concatenate([[0.0], np.cumsum(np.where(up_flag, vals, 0.0))[:-1]])
    cum_sd = np.concatenate([[0.0], np.cumsum(np.where(down_flag, vals, 0.0))[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_up = cum_up / cum_n
        p_down = cum_down / cum_n
        avg_up = cum_su / np.where(cum_up > 0, cum_up, 1)
        avg_down = cum_sd / np.where(cum_down > 0, cum_down, 1)
        dec_up = (cum_n >= min_n) & (p_up >= min_p) & (avg_up >= min_abs)
        dec_down = (cum_n >= min_n) & (p_down >= min_p) & (avg_down <= -min_abs)
    trade_mask = dec_up | dec_down
    decisions = np.where(dec_up, "predict_up", np.where(dec_down, "predict_down", "no_trade"))
    return ev_dates, vals, trade_mask, decisions


def combo_stats(
    mask: pd.Series,
    target: pd.Series,
    dates: pd.Series,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> dict:
    ev_dates, vals, trade_mask, decisions = evaluate(mask, target, dates, min_n, min_p, min_abs)
    out = {
        "full_avg": float("nan"),
        "full_trades": 0,
        "frozen_avg": float("nan"),
        "frozen_trades": 0,
        "frozen_hit": float("nan"),
    }
    if not trade_mask.any():
        return out
    trade_dates = ev_dates[trade_mask]
    trade_vals = vals[trade_mask]
    trade_dec = decisions[trade_mask]
    out["full_avg"] = float(trade_vals.mean())
    out["full_trades"] = int(trade_vals.size)
    hold = trade_dates >= CUTOFF
    if hold.any():
        hv = trade_vals[hold]
        hd = trade_dec[hold]
        out["frozen_avg"] = float(hv.mean())
        out["frozen_trades"] = int(hv.size)
        out["frozen_hit"] = float(
            (((hd == "predict_up") & (hv > 0)) | ((hd == "predict_down") & (hv < 0))).mean()
        )
    return out


def is_dual_pass(stats: dict) -> bool:
    return (
        stats["full_avg"] == stats["full_avg"]
        and abs(stats["full_avg"]) >= 0.2
        and stats["full_trades"] >= 50
        and stats["frozen_avg"] == stats["frozen_avg"]
        and abs(stats["frozen_avg"]) >= 0.2
        and stats["frozen_trades"] >= 10
        and stats["frozen_hit"] == stats["frozen_hit"]
        and stats["frozen_hit"] >= 0.45
    )


def build_master() -> pd.DataFrame:
    fund = wf.load_panel(FUND_PANEL)
    etf19 = wf.load_panel(ETF19)
    ext = pd.read_csv(EXT_COMBINED, skiprows=12)
    ext["Date"] = pd.to_datetime(ext["Date"], format="%m/%d/%Y")
    external = pd.read_csv(EXTERNAL_DAILY, parse_dates=["Date"])
    ext_keep = ["Date"] + [
        c
        for c in external.columns
        if c.startswith(("VIX", "TNX", "Credit", "JNK", "USD", "Sect", "Yld", "Stk"))
    ]
    external = external[ext_keep]
    master = (
        fund.merge(etf19, on="Date", how="left")
        .merge(ext, on="Date", how="left")
        .merge(external, on="Date", how="left")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return master


def build_masks(master: pd.DataFrame) -> dict[str, pd.Series]:
    etf19 = master[["Date"] + list(wf.load_panel(ETF19).columns[1:])]
    cond_map = wf.build_condition_map(etf19)
    all_etfs = list(etf19.columns[1:]) + list(pd.read_csv(EXT_COMBINED, skiprows=12).columns[1:])
    masks = dict(cond_map)
    for etf in all_etfs:
        s = master[etf]
        masks[f"{etf}_up"] = s > 0
        masks[f"{etf}_down"] = s < 0
        masks[f"{etf}_big_up"] = s >= 1.0
        masks[f"{etf}_big_down"] = s <= -1.0
        masks[f"{etf}_gt2"] = s > 2.0
        masks[f"{etf}_lt-2"] = s < -2.0
    masks["ext_vix_chg_ge5"] = master["VIX_Chg%"] >= 5
    masks["ext_vix_chg_le-5"] = master["VIX_Chg%"] <= -5
    masks["ext_vix5d_ge10"] = master["VIX_5dChg"] >= 10
    masks["ext_vix5d_le-10"] = master["VIX_5dChg"] <= -10
    masks["ext_vix_ge25"] = master["VIX_Close"] >= 25
    masks["ext_vix_le15"] = master["VIX_Close"] <= 15
    masks["ext_tnx_bp_ge10"] = master["TNX_ChgBp"] >= 10
    masks["ext_tnx_bp_le-10"] = master["TNX_ChgBp"] <= -10
    return masks


def self_mask(master: pd.DataFrame, ticker: str, name: str) -> pd.Series:
    r = master[ticker]
    if name == "self_up":
        return r > 0
    if name == "self_down":
        return r < 0
    if name == "self_big_up":
        return r >= 0.02
    if name == "self_big_down":
        return r <= -0.02
    if name == "self_3up":
        return (r > 0) & (r.shift(1) > 0) & (r.shift(2) > 0)
    if name == "self_3down":
        return (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0)
    raise ValueError(f"unknown self condition {name}")


def composite_mask(master: pd.DataFrame, condition: str, all_etfs: set[str]) -> pd.Series:
    tokens = condition.split("_")
    if len(tokens) == 4 and tokens[0] in all_etfs and tokens[2] in all_etfs:
        a, sa, b, sb = tokens
        ma = master[a] > 0 if sa == "up" else master[a] < 0
        mb = master[b] > 0 if sb == "up" else master[b] < 0
        return ma & mb
    raise ValueError(f"cannot parse composite {condition}")


def get_mask(
    master: pd.DataFrame,
    masks: dict[str, pd.Series],
    ticker: str,
    condition: str,
    all_etfs: set[str],
) -> pd.Series:
    if condition.startswith("self_"):
        return self_mask(master, ticker, condition)
    if condition in masks:
        return masks[condition]
    return composite_mask(master, condition, all_etfs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    FULL_OUT.mkdir(parents=True, exist_ok=True)
    FROZEN_OUT.mkdir(parents=True, exist_ok=True)
    master = build_master()
    masks = build_masks(master)
    all_etfs = {
        c
        for c in master.columns
        if c not in {"Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp",
                     "CreditSpread", "JNKSpread", "StkBonCorr", "USDGoldRatio",
                     "SectRotation", "VIX_5dChg", "VIX_20dVol", "VIX_TNX_Ratio",
                     "YldCurveProxy"}
        and c not in set(wf.load_panel(FUND_PANEL).columns[1:])
    }
    fund_cols = set(wf.load_panel(FUND_PANEL).columns[1:])
    dates = master["Date"]

    candidates: list[dict] = []

    # A. Main model candidates (strict rule, 1-day)
    stable = pd.read_csv(STABLE)
    for _, row in stable.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        if condition not in masks:
            continue
        stats = combo_stats(masks[condition], master[ticker].shift(-1), dates, 100, 0.55, 0.2)
        candidates.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "source": "main",
                "condition": condition,
                "horizon": 1,
                **stats,
                "dual_pass": is_dual_pass(stats),
            }
        )

    # B. Sparse candidates (relaxed rule)
    sparse = pd.read_csv(SPARSE_BOSS, keep_default_na=False)
    for _, row in sparse.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        stats = combo_stats(mask, get_target(master, ticker, horizon), dates, 100, 0.52, 0.15)
        candidates.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "source": "sparse",
                "condition": condition,
                "horizon": horizon,
                **stats,
                "dual_pass": is_dual_pass(stats),
            }
        )

    # C. Optimization scan candidates (relaxed rule, new ETF singles)
    opt = pd.read_csv(OPT_SCAN)
    for i, row in enumerate(opt.itertuples(index=False)):
        ticker = row.ticker
        condition = row.condition
        horizon = int(row.horizon)
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        stats = combo_stats(mask, get_target(master, ticker, horizon), dates, 100, 0.52, 0.15)
        candidates.append(
            {
                "ticker": ticker,
                "fund_group": em.fund_group(ticker),
                "source": "optimization_scan",
                "condition": condition,
                "horizon": horizon,
                **stats,
                "dual_pass": is_dual_pass(stats),
            }
        )
        if (i + 1) % 2000 == 0:
            print(f"optimization scan {i + 1}/{len(opt)}", flush=True)

    pool = pd.DataFrame(candidates)
    covered = set(pool.loc[pool["dual_pass"], "ticker"])

    # D. Gap-fund extra strategies
    gap_funds = sorted(fund_cols - MONEY - covered)
    print(f"gap funds after A/B/C: {len(gap_funds)}", flush=True)
    ext_rows = []
    for gi, ticker in enumerate(gap_funds):
        fr = master[ticker]
        corrs = []
        for etf in sorted(all_etfs):
            c = fr.corr(master[etf])
            if c == c:
                corrs.append((etf, abs(c)))
        corrs.sort(key=lambda x: x[1], reverse=True)
        top_etfs = [e for e, _ in corrs[:5]]
        refs = {}
        for etf in top_etfs:
            refs[etf] = "QQQ" if etf == "SPY" else "SPY"
        conditions = []
        for etf in sorted(all_etfs):
            for name in ["up", "down", "big_up", "big_down", "gt2", "lt-2"]:
                conditions.append((f"{etf}_{name}", None))
        for etf in top_etfs:
            ref = refs[etf]
            for sa, sb in [("up", "up"), ("down", "down"), ("up", "down"), ("down", "up")]:
                conditions.append((f"{etf}_{sa}_{ref}_{sb}", None))
        for name in ["ext_vix_chg_ge5", "ext_vix_chg_le-5", "ext_vix5d_ge10", "ext_vix5d_le-10",
                     "ext_vix_ge25", "ext_vix_le15", "ext_tnx_bp_ge10", "ext_tnx_bp_le-10"]:
            conditions.append((name, None))
        for condition, _ in conditions:
            for horizon in [1, 2, 3, 5]:
                mask = get_mask(master, masks, ticker, condition, all_etfs)
                stats = combo_stats(mask, get_target(master, ticker, horizon), dates, 100, 0.52, 0.15)
                if is_dual_pass(stats):
                    ext_rows.append(
                        {
                            "ticker": ticker,
                            "fund_group": em.fund_group(ticker),
                            "source": "gap_extra",
                            "condition": condition,
                            "horizon": horizon,
                            **stats,
                            "dual_pass": True,
                        }
                    )
        if (gi + 1) % 5 == 0:
            print(f"gap funds scanned {gi + 1}/{len(gap_funds)}", flush=True)
    if ext_rows:
        pool = pd.concat([pool, pd.DataFrame(ext_rows)], ignore_index=True)

    pool = pool.drop_duplicates(subset=["ticker", "condition", "horizon", "source"], keep="first")
    pool.to_csv(CANDIDATES, index=False)
    dual = pool[pool["dual_pass"]].copy()
    dual = dual.sort_values(["full_avg"], key=lambda s: s.abs(), ascending=False)
    dual.to_csv(OUT_DIR / "dual_criteria_pass.csv", index=False)

    best_rows = []
    for ticker, group in dual.groupby("ticker"):
        row = group.reindex(group["full_avg"].abs().sort_values(ascending=False).index).iloc[0]
        best_rows.append(row)
    best = pd.DataFrame(best_rows).sort_values("ticker") if best_rows else pd.DataFrame(
        columns=["ticker", "fund_group", "source", "condition", "horizon", "full_avg", "full_trades",
                 "frozen_avg", "frozen_trades", "frozen_hit", "dual_pass"]
    )
    best.to_csv(SUMMARY, index=False)

    # E. Fit matrix and ETF effectiveness
    fit_rows = []
    for etf in sorted(all_etfs):
        etf_ret = master[etf]
        for fund_col in sorted(fund_cols):
            fund_ret = master[fund_col]
            valid = master[etf_ret.notna() & fund_ret.notna()]
            if len(valid) < 60:
                continue
            same = float(valid[etf].corr(valid[fund_col]))
            tomorrow = valid[fund_col].shift(-1)
            both = pd.concat([valid[etf], tomorrow], axis=1).dropna()
            lead1 = float(both.iloc[:, 0].corr(both.iloc[:, 1])) if len(both) > 60 else float("nan")
            agree = float(
                (((both.iloc[:, 0] > 0) & (both.iloc[:, 1] > 0)) |
                 ((both.iloc[:, 0] < 0) & (both.iloc[:, 1] < 0))).mean()
            ) if len(both) > 60 else float("nan")
            fund_dual = dual[(dual["ticker"] == fund_col)]
            has = bool(((fund_dual["condition"].str.split("_").apply(lambda t: etf in t))).any()) if not fund_dual.empty else False
            fit_rows.append(
                {
                    "ETF": etf,
                    "Fund": fund_col,
                    "Same": round(same, 4),
                    "Lead1": round(lead1, 4) if lead1 == lead1 else "",
                    "DirAgree": round(agree, 4) if agree == agree else "",
                    "has_dual_signal": has,
                }
            )
    fit = pd.DataFrame(fit_rows)
    fit.to_csv(FIT_MATRIX, index=False)

    def etfs_of(condition: str) -> list[str]:
        return [t for t in condition.split("_") if t in all_etfs]

    eff_rows = []
    for etf in sorted(all_etfs):
        affected = dual[dual["condition"].apply(lambda c: etf in etfs_of(c))]
        eff_rows.append(
            {
                "ETF": etf,
                "effective_funds": affected["ticker"].nunique(),
                "suggestion": "delete" if affected.empty else "keep",
            }
        )
    eff = pd.DataFrame(eff_rows).sort_values("effective_funds", ascending=False)
    eff.to_csv(ETF_EFFECT, index=False)

    zero_etfs = set(eff.loc[eff["effective_funds"] == 0, "ETF"])
    covered_after = set()
    for _, row in dual.iterrows():
        etfs = etfs_of(row["condition"])
        if etfs and all(e in zero_etfs for e in etfs):
            continue
        covered_after.add(row["ticker"])
    lost = sorted(covered - covered_after)

    # F. Formal outputs
    generated = 0
    for _, row in dual.iterrows():
        ticker = row["ticker"]
        condition = row["condition"]
        horizon = int(row["horizon"])
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        target = get_target(master, ticker, horizon)
        ev_dates, vals, trade_mask, decisions = evaluate(mask, target, dates, 100, 0.52, 0.15)
        td = ev_dates[trade_mask]
        tv = vals[trade_mask]
        if not td.size:
            continue
        full_rows = [
            (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
            for d, v in sorted(zip(td, tv), key=lambda x: x[0], reverse=True)
        ]
        hold = td >= CUTOFF
        frozen_rows = [
            (pd.Timestamp(d).strftime("%m/%d/%Y"), float(v))
            for d, v in sorted(zip(td[hold], tv[hold]), key=lambda x: x[0], reverse=True)
        ]
        name = f"{ticker}__{condition}" + (f"__N{horizon}" if horizon > 1 else "")
        write_standard_csv(FULL_OUT / f"{name}.csv", full_rows)
        if frozen_rows:
            write_standard_csv(FROZEN_OUT / f"{name}.csv", frozen_rows)
            generated += 1

    print(f"candidates: {len(pool)}")
    print(f"dual pass: {len(dual)}")
    print(f"dual coverage funds: {len(covered)}")
    print(f"gap funds scanned: {len(gap_funds)}")
    print(f"remaining funds: {len(fund_cols - MONEY - covered)}")
    print(sorted(fund_cols - MONEY - covered))
    print(f"ETFs with zero contribution: {len(zero_etfs)} {sorted(zero_etfs)}")
    print(f"funds lost after deleting zero-ETF: {len(lost)} {lost}")
    print(f"formal frozen CSVs generated: {generated}")
    print(f"Saved: {CANDIDATES}")
    print(f"Saved: {SUMMARY}")
    print(f"Saved: {FIT_MATRIX}")
    print(f"Saved: {ETF_EFFECT}")


if __name__ == "__main__":
    main()
