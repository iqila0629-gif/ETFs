"""Build a delivery-preview folder inside adj_close_v3 (Adj Close path).

The preview intentionally keeps simple CSV/text outputs so content can be
reviewed before the final delivery folders are replaced. It combines:
  - v3 single-condition pass (Adj Close rerun of the old candidate pool)
  - exhaustive pairwise ETF scan strict pass (all 76 ETFs, 1/2/3-day)
and selects one best strategy per fund.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENT = ROOT / "analysis_results" / "event_study"
PROC = ROOT / "processed_returns"
V3 = ROOT / "analysis_results" / "adj_close_v3"
OUT = V3 / "delivery_preview"

sys.path.insert(0, str(EVENT))

from event_metrics import fund_group  # noqa: E402
from generate_daily_tables import write_daily_wide  # noqa: E402
from generate_predictions import write_standard_csv  # noqa: E402


CUTOFF = np.datetime64("2025-01-01")
NON_FUND = {
    "Date",
    "VIX_Close",
    "VIX_Chg%",
    "TNX_Yield",
    "TNX_ChgBp",
    "CreditSpread",
    "JNKSpread",
    "StkBonCorr",
    "USDGoldRatio",
    "SectRotation",
    "VIX_5dChg",
    "VIX_20dVol",
    "VIX_TNX_Ratio",
    "YldCurveProxy",
}


def build_master() -> pd.DataFrame:
    fund = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in fund.columns:
        fund = fund.rename(columns={"date": "Date"})
    etf19 = pd.read_csv(EVENT / "panel_etf_returns_adj.csv")
    ext = pd.read_csv(PROC / "combined_extended_etf_returns_adj.csv", skiprows=12)
    external = pd.read_csv(EVENT / "external_daily.csv", parse_dates=["Date"])
    keep = ["Date"] + [
        c
        for c in external.columns
        if c.startswith(("VIX", "TNX", "Credit", "JNK", "USD", "Sect", "Yld", "Stk"))
    ]
    external = external[keep]
    for df in (fund, etf19, ext):
        df["Date"] = pd.to_datetime(df["Date"])
    master = (
        fund.merge(etf19, on="Date", how="left")
        .merge(ext, on="Date", how="left")
        .merge(external, on="Date", how="left")
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


def params_for(source: str) -> tuple[int, float, float]:
    return (100, 0.55, 0.2) if source == "main" else (100, 0.52, 0.15)


def multi_day_target(
    master: pd.DataFrame,
    ticker: str,
    horizon: int,
    strict_finite: bool = False,
) -> np.ndarray:
    arr = master[ticker].to_numpy(dtype=float)
    n = arr.size
    if horizon == 1:
        out = np.empty(n, dtype=float)
        out[:-1] = arr[1:]
        out[-1] = np.nan
        return out
    shifted = np.column_stack([np.roll(arr, -k) for k in range(1, horizon + 1)])
    shifted[-horizon:, :] = np.nan
    if strict_finite:
        return np.mean(shifted, axis=1)
    return np.nanmean(shifted, axis=1)


_target_cache: dict[tuple[str, int], np.ndarray] = {}


def get_target(
    master: pd.DataFrame,
    ticker: str,
    horizon: int,
    strict_finite: bool = False,
) -> np.ndarray:
    key = (ticker, horizon, strict_finite)
    if key not in _target_cache:
        _target_cache[key] = multi_day_target(master, ticker, horizon, strict_finite)
    return _target_cache[key]


def evaluate_signal(
    mask: pd.Series,
    target: np.ndarray,
    dates: np.ndarray,
    min_n: int,
    min_p: float,
    min_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target)
    idx = np.flatnonzero(valid)
    if idx.size == 0:
        empty = np.array([], dtype=dates.dtype)
        return empty, np.array([], dtype=float), np.array([], dtype=bool), np.array([], dtype=float)
    ev_dates = dates[idx]
    vals = target[idx] * 100.0
    n = vals.size
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
    predicted = np.where(
        dec_up,
        avg_up,
        np.where(dec_down, avg_down, np.nan),
    )
    return ev_dates, vals, trade_mask, predicted


def load_pool() -> pd.DataFrame:
    v3 = pd.read_csv(V3 / "v3_dual_criteria_pass.csv", keep_default_na=False)
    strict = pd.read_csv(V3 / "pair_strict_pass.csv", keep_default_na=False)
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
    pool = pd.concat([v3[cols], strict[cols]], ignore_index=True)
    pool["fund_group"] = pool["ticker"].map(fund_group)
    pool["abs_full_avg"] = pool["full_avg"].abs()
    pool = pool.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
        ascending=False,
    )
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    return pool.reset_index(drop=True)


def load_pair_candidates_for(tickers: list[str]) -> pd.DataFrame:
    path = V3 / "pair_candidates_stats.csv"
    keep = [
        "full_avg",
        "full_trades",
        "full_hit",
        "frozen_avg",
        "frozen_trades",
        "frozen_hit",
        "ticker",
        "fund_group",
        "source",
        "condition",
        "horizon",
        "strict_pass",
        "frozen_pass",
    ]
    wanted = set(tickers)
    chunks = []
    for chunk in pd.read_csv(path, usecols=keep, chunksize=300_000):
        sub = chunk[chunk["ticker"].isin(wanted)]
        if not sub.empty:
            chunks.append(sub)
    if not chunks:
        return pd.DataFrame(columns=keep)
    return pd.concat(chunks, ignore_index=True)


def write_wide(path: pathlib.Path, dates_desc: list[pd.Timestamp], tickers: list[str], mapping: dict[str, dict[pd.Timestamp, float]]) -> None:
    write_daily_wide(path, dates_desc, tickers, mapping)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    (OUT / "关键成果" / "未覆盖基金评估").mkdir(parents=True, exist_ok=True)
    (OUT / "关键成果" / "正式预测_最佳策略_全历史").mkdir(parents=True, exist_ok=True)
    (OUT / "关键成果" / "正式预测_最佳策略_冻结期").mkdir(parents=True, exist_ok=True)
    (OUT / "中间文档" / "脚本").mkdir(parents=True, exist_ok=True)
    (OUT / "中间文档" / "文件").mkdir(parents=True, exist_ok=True)
    (OUT / "数据" / "数据_处理后合并").mkdir(parents=True, exist_ok=True)

    print("loading master", flush=True)
    master = build_master()
    fund_panel = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in fund_panel.columns:
        fund_panel = fund_panel.rename(columns={"date": "Date"})
    all_tickers = list(fund_panel.columns[1:])
    fund_set = set(all_tickers)
    all_etfs = {
        c
        for c in master.columns
        if c not in fund_set and c not in NON_FUND
    }
    dates = master["Date"].to_numpy()
    dates_desc = list(pd.to_datetime(master["Date"]).sort_values(ascending=False))
    mask_cache: dict[tuple[str, str | None], pd.Series] = {}

    def get_mask(condition: str, ticker: str) -> pd.Series:
        key: tuple[str, str | None] = (condition, ticker if condition.startswith("self_") else None)
        if key not in mask_cache:
            mask_cache[key] = build_condition_mask(master, condition, ticker, all_etfs)
        return mask_cache[key]

    print("loading signal pool", flush=True)
    pool = load_pool()
    pool.to_csv(OUT / "关键成果" / "v3_正式信号_全量.csv", index=False)
    print("pool signals", len(pool), "funds", pool["ticker"].nunique(), flush=True)

    # Best one strategy per fund (same priority as the old delivery: |full avg|,
    # then frozen hit, then full hit).
    best = (
        pool.sort_values(
            ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
            ascending=False,
        )
        .groupby("ticker", sort=True)
        .head(1)
        .sort_values("ticker")
        .reset_index(drop=True)
    )
    best["decision"] = np.where(best["full_avg"] > 0, "predict_up", "predict_down")
    best.to_csv(OUT / "关键成果" / "v3_每基金最佳策略.csv", index=False)
    print("best funds", len(best), flush=True)

    # Recompute daily trigger records for the best strategies and write the
    # per-signal company CSVs plus a long-format detail table.
    detail_rows: list[dict] = []
    best_by_fund: dict[str, dict[pd.Timestamp, float]] = {t: {} for t in all_tickers}
    for _, row in best.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        source = str(row["source"])
        mask = get_mask(condition, ticker)
        target = get_target(master, ticker, horizon, strict_finite=source == "pair_scan")
        ev_dates, vals, tm, pred = evaluate_signal(mask, target, dates, *params_for(source))
        if not tm.any():
            continue
        td = ev_dates[tm]
        tv = vals[tm]
        tp = pred[tm]
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
        write_standard_csv(OUT / "关键成果" / "正式预测_最佳策略_全历史" / f"{name}.csv", full_rows)
        if frozen_rows:
            write_standard_csv(OUT / "关键成果" / "正式预测_最佳策略_冻结期" / f"{name}.csv", frozen_rows)
        for d, v, pr in zip(td, tv, tp):
            best_by_fund[ticker][pd.Timestamp(d)] = float(v)
            detail_rows.append(
                {
                    "ticker": ticker,
                    "fund_group": fund_group(ticker),
                    "condition": condition,
                    "horizon": horizon,
                    "date": pd.Timestamp(d).strftime("%m/%d/%Y"),
                    "predicted_return": float(pr),
                    "actual_return": float(v),
                }
            )
    pd.DataFrame(detail_rows).to_csv(
        OUT / "关键成果" / "v3_信号逐日明细_最佳策略.csv",
        index=False,
    )
    write_wide(
        OUT / "关键成果" / "v3_公司格式_最佳策略_全历史.csv",
        dates_desc,
        all_tickers,
        best_by_fund,
    )
    frozen_best = {
        t: {d: v for d, v in m.items() if d >= pd.Timestamp(CUTOFF)}
        for t, m in best_by_fund.items()
    }
    write_wide(
        OUT / "关键成果" / "v3_公司格式_最佳策略_冻结期.csv",
        [d for d in dates_desc if d >= pd.Timestamp(CUTOFF)],
        all_tickers,
        frozen_best,
    )
    print("best daily tables done", flush=True)

    # R4 merge for the full signal pool: same fund, same day -> strongest
    # |full-history average| wins. This is the only heavy loop.
    all_by_fund: dict[str, dict[np.datetime64, tuple[float, float]]] = {
        t: {} for t in all_tickers
    }
    for i, row in enumerate(pool.itertuples(index=False)):
        ticker = str(row.ticker)
        condition = str(row.condition)
        horizon = int(row.horizon)
        source = str(row.source)
        mask = get_mask(condition, ticker)
        target = get_target(master, ticker, horizon, strict_finite=source == "pair_scan")
        ev_dates, vals, tm, _ = evaluate_signal(mask, target, dates, *params_for(source))
        if not tm.any():
            continue
        strength = abs(float(row.full_avg))
        rec = all_by_fund[ticker]
        for d, v in zip(ev_dates[tm], vals[tm]):
            old = rec.get(d)
            if old is None or strength > old[1]:
                rec[d] = (float(v), strength)
        if (i + 1) % 5000 == 0:
            print(f"R4 merge {i + 1}/{len(pool)}", flush=True)

    all_plain = {
        t: {pd.Timestamp(d): v for d, (v, _s) in m.items()}
        for t, m in all_by_fund.items()
    }
    write_wide(
        OUT / "关键成果" / "v3_公司格式_全信号_全历史.csv",
        dates_desc,
        all_tickers,
        all_plain,
    )
    frozen_all = {
        t: {d: v for d, v in m.items() if d >= pd.Timestamp(CUTOFF)}
        for t, m in all_plain.items()
    }
    write_wide(
        OUT / "关键成果" / "v3_公司格式_全信号_冻结期.csv",
        [d for d in dates_desc if d >= pd.Timestamp(CUTOFF)],
        all_tickers,
        frozen_all,
    )
    print("all-signal daily tables done", flush=True)

    # ETF usage.
    def etfs_in(condition: str) -> list[str]:
        return [t for t in condition.split("_") if t in all_etfs]

    etf_rows = []
    for e in sorted(all_etfs):
        in_pool = pool[pool["condition"].apply(lambda c: e in etfs_in(c))]
        in_best = best[best["condition"].apply(lambda c: e in etfs_in(c))]
        etf_rows.append(
            {
                "ETF": e,
                "in_best": bool(len(in_best)),
                "best_signals": len(in_best),
                "best_funds": int(in_best["ticker"].nunique()),
                "all_signals": len(in_pool),
                "all_funds": int(in_pool["ticker"].nunique()),
            }
        )
    etf_usage = pd.DataFrame(etf_rows).sort_values(
        ["all_signals", "all_funds"], ascending=False
    )
    etf_usage.to_csv(OUT / "关键成果" / "v3_ETF使用统计.csv", index=False)

    # Coverage table for all 129 funds.
    covered = set(best["ticker"])
    coverage_rows = []
    for t in all_tickers:
        if t in covered:
            b = best[best["ticker"] == t].iloc[0]
            coverage_rows.append(
                {
                    "ticker": t,
                    "fund_group": fund_group(t),
                    "covered": True,
                    "condition": b["condition"],
                    "horizon": b["horizon"],
                    "full_avg": b["full_avg"],
                    "full_trades": b["full_trades"],
                    "full_hit": b["full_hit"],
                    "frozen_avg": b["frozen_avg"],
                    "frozen_trades": b["frozen_trades"],
                    "frozen_hit": b["frozen_hit"],
                    "reason": "",
                }
            )
        else:
            coverage_rows.append(
                {
                    "ticker": t,
                    "fund_group": fund_group(t),
                    "covered": False,
                    "condition": "",
                    "horizon": "",
                    "full_avg": "",
                    "full_trades": "",
                    "full_hit": "",
                    "frozen_avg": "",
                    "frozen_trades": "",
                    "frozen_hit": "",
                    "reason": "money_fund" if t in {"MPIXX", "MPSXX"} else "not_qualified",
                }
            )
    pd.DataFrame(coverage_rows).to_csv(
        OUT / "关键成果" / "v3_覆盖情况.csv",
        index=False,
    )
    print("ETF usage and coverage done", flush=True)

    # Uncovered funds evaluation (money funds excluded).
    uncovered = [t for t in all_tickers if t not in covered and t not in {"MPIXX", "MPSXX"}]
    v3_cand = pd.read_csv(V3 / "v3_candidates_stats.csv", keep_default_na=False)
    v3_cand = v3_cand[v3_cand["ticker"].isin(uncovered)]
    pair_cand = load_pair_candidates_for(uncovered)
    cand = pd.concat([v3_cand, pair_cand], ignore_index=True)
    cand = cand.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    for col in [
        "full_avg",
        "full_trades",
        "full_hit",
        "frozen_avg",
        "frozen_trades",
        "frozen_hit",
    ]:
        cand[col] = pd.to_numeric(cand[col], errors="coerce")
    cand["abs_full_avg"] = cand["full_avg"].abs()
    cand["abs_frozen_avg"] = cand["frozen_avg"].abs()
    cand = cand.sort_values(
        ["ticker", "frozen_hit", "abs_frozen_avg", "abs_full_avg"],
        ascending=[True, False, False, False],
    )
    cand.to_csv(OUT / "关键成果" / "未覆盖基金评估" / "v3_未覆盖_全部候选重算.csv", index=False)

    def tier_of(r: pd.Series) -> str:
        fa = r.get("frozen_avg")
        ft = r.get("frozen_trades", 0)
        fh = r.get("frozen_hit")
        if fa == fa and abs(float(fa)) >= 0.2 and int(ft) >= 10 and fh == fh and float(fh) >= 0.55:
            return "tier1_frozen_pass"
        if fa == fa and abs(float(fa)) >= 0.2 and int(ft) < 10:
            return "tier2_small_sample"
        return "tier3_no_frozen_pass"

    cand["tier"] = cand.apply(tier_of, axis=1)
    for tier, name in [
        ("tier1_frozen_pass", "v3_未覆盖_第一档_冻结期已达标.csv"),
        ("tier2_small_sample", "v3_未覆盖_第二档_冻结期达标样本小.csv"),
        ("tier3_no_frozen_pass", "v3_未覆盖_第三档_冻结期未达标.csv"),
    ]:
        sub = cand[cand["tier"] == tier]
        if not sub.empty:
            near = sub.groupby("ticker").head(1).sort_values("ticker")
        else:
            near = sub
        near.to_csv(OUT / "关键成果" / "未覆盖基金评估" / name, index=False)
        print(name, "funds", near["ticker"].nunique() if len(near) else 0, flush=True)

    # Keep small intermediate copies inside the preview.
    for src, dst in [
        (V3 / "v3_candidates_stats.csv", OUT / "中间文档" / "文件" / "v3_candidates_stats.csv"),
        (V3 / "pair_strict_pass.csv", OUT / "中间文档" / "文件" / "pair_strict_pass.csv"),
        (V3 / "pair_frozen_pass.csv", OUT / "中间文档" / "文件" / "pair_frozen_pass.csv"),
        (EVENT / "panel_fund_returns_adj.csv", OUT / "中间文档" / "文件" / "panel_fund_returns_adj.csv"),
        (EVENT / "panel_etf_returns_adj.csv", OUT / "中间文档" / "文件" / "panel_etf_returns_adj.csv"),
    ]:
        if src.exists():
            import shutil

            shutil.copy2(src, dst)

    print("all done", flush=True)


if __name__ == "__main__":
    main()
