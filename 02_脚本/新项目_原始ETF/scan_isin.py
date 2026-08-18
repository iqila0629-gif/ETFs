# -*- coding: utf-8 -*-
"""Phase 2 (v2): 251 支 ISIN 穷举扫描。条件空间 19 ETF x 6 方向 x horizon 1/2/3 = 342。
输出（04_结果/新项目_原始ETF/中间结果/）:
  eip_single_pass_v2.csv            全部信号(含 pass 标记) —— 穷举表
  eip_threshold_sensitivity_v2.csv  门槛敏感性网格
  eip_single_baseline_pass_v2.csv   推荐门槛通过信号(含基金名)
  eip_single_best_strategy_v2.csv   每基金最优策略
  eip_uncovered_v2.csv              无策略基金
并打印实际统计供回填规划 5.3 表。
"""
import pathlib, sys, time, os
import numpy as np
import pandas as pd

import config_eip as config

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
PANEL = D / "新项目_processed" / "eip_panel_251etf.csv"
MIDDLE = BASE / "04_结果" / "新项目_原始ETF" / "中间结果"
MIDDLE.mkdir(parents=True, exist_ok=True)
NAME_MAP = D / "eip_isin_name_map.csv"

CUTOFF = np.datetime64(config.CUTOFF)

def build_target(fund_arr, horizon):
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

def evaluate_mask(mask, target_col, dates, min_n, min_p, min_abs):
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

def build_etf_mask(master, condition):
    tokens = condition.split("_")
    etf = tokens[0]
    suffix = "_".join(tokens[1:])
    s = master[etf]
    if suffix == "up": return (s > 0).to_numpy(dtype=bool)
    if suffix == "down": return (s < 0).to_numpy(dtype=bool)
    if suffix == "big_up": return (s >= 1.0).to_numpy(dtype=bool)
    if suffix == "big_down": return (s <= -1.0).to_numpy(dtype=bool)
    if suffix == "gt2": return (s > 2.0).to_numpy(dtype=bool)
    if suffix == "lt-2": return (s < -2.0).to_numpy(dtype=bool)
    raise ValueError(condition)

def pass_flags(df, full_min, frozen_min):
    return (
        df["full_avg"].abs().ge(config.MIN_ABS_AVG)
        & df["full_trades"].ge(full_min)
        & df["full_hit"].gt(config.MIN_FULL_HIT)
        & df["frozen_avg"].abs().ge(config.MIN_ABS_AVG)
        & df["frozen_trades"].ge(frozen_min)
        & df["frozen_hit"].ge(config.MIN_FROZEN_HIT)
    )

def best_per_fund(df):
    if df.empty:
        return df
    df = df.copy()
    df["abs_full_avg"] = df["full_avg"].abs()
    return (df.sort_values(["abs_full_avg","frozen_hit","full_hit","frozen_trades"], ascending=False)
              .groupby("ticker", sort=True).head(1).sort_values("ticker").reset_index(drop=True))

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    panel = pd.read_csv(PANEL)
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel = panel.sort_values("Date").reset_index(drop=True)
    fund_cols = [c for c in panel.columns if c not in {"Date"} | set(config.ORIGINAL19)]
    print("panel rows:", len(panel), "funds:", len(fund_cols), flush=True)
    dates = panel["Date"].to_numpy()
    fund_arr = panel[fund_cols].to_numpy(dtype=float)
    targets = {h: build_target(fund_arr, h) for h in config.HORIZONS}
    conditions = [f"{etf}_{suffix}" for etf in sorted(config.ORIGINAL19) for suffix in ["up","down","big_up","big_down","gt2","lt-2"]]
    rows = []
    n_checked = 0
    skipped_noevents = 0
    skipped_notrade = 0
    for cond in conditions:
        mask = build_etf_mask(panel, cond)
        for horizon in config.HORIZONS:
            target = targets[horizon]
            for fi, ticker in enumerate(fund_cols):
                tcol = target[:, fi]
                valid = mask & np.isfinite(tcol)
                if int(valid.sum()) < config.RAW_EVENT_MIN:
                    skipped_noevents += 1
                    continue
                if int((valid & (dates >= CUTOFF)).sum()) < config.RECOMMENDED_FROZEN_TRADES:
                    skipped_noevents += 1
                    continue
                ev_dates, vals, trade_mask = evaluate_mask(mask, tcol, dates, config.DECISION_N, config.DECISION_P, config.DECISION_ABS)
                if not trade_mask.any():
                    skipped_notrade += 1
                    continue
                td = ev_dates[trade_mask]
                tv = vals[trade_mask]
                hold = td >= CUTOFF
                row = {"ticker": ticker, "condition": cond, "horizon": horizon, "source": "single_scan",
                       "full_avg": float(tv.mean()), "full_trades": int(tv.size), "full_hit": float((tv > 0).mean()),
                       "frozen_avg": float(tv[hold].mean()) if hold.any() else float("nan"),
                       "frozen_trades": int(hold.sum()), "frozen_hit": float((tv[hold] > 0).mean()) if hold.any() else float("nan")}
                row["pass"] = bool(abs(row["full_avg"]) >= config.MIN_ABS_AVG and row["full_trades"] >= config.RECOMMENDED_FULL_TRADES
                                   and row["full_hit"] > config.MIN_FULL_HIT and row["frozen_avg"] == row["frozen_avg"]
                                   and abs(row["frozen_avg"]) >= config.MIN_ABS_AVG and row["frozen_trades"] >= config.RECOMMENDED_FROZEN_TRADES
                                   and row["frozen_hit"] >= config.MIN_FROZEN_HIT)
                rows.append(row)
            n_checked += 1
        if n_checked % 57 == 0:
            print(f"  checked {n_checked}/{len(conditions)*3}  signals={len(rows)}  elapsed={time.time()-t0:.0f}s", flush=True)
    pool = pd.DataFrame(rows)
    pool.to_csv(MIDDLE / "eip_single_pass_v2.csv", index=False, encoding="utf-8-sig")
    print("evaluated signals:", len(pool), flush=True)
    print("funds with any signal:", pool["ticker"].nunique(), flush=True)
    print("skipped (events<220 or frozen<30):", skipped_noevents, " skipped (no trade trigger):", skipped_notrade, flush=True)

    # name map
    mrows = list(pd.read_csv(NAME_MAP, encoding="utf-8-sig").to_dict("records")) if NAME_MAP.exists() else []
    if not mrows:
        mrows = []
    name_map = {r["isin"]: r["name"] for r in mrows}

    # threshold sensitivity
    sens = []
    for full_min in config.THRESHOLD_GRID_FULL:
        for frozen_min in config.THRESHOLD_GRID_FROZEN:
            ok = pool[pass_flags(pool, full_min, frozen_min)]
            best = best_per_fund(ok)
            sens.append({"full_min_trades": full_min, "frozen_min_trades": frozen_min,
                         "signals": len(ok), "covered_funds": best["ticker"].nunique() if len(best) else 0})
    pd.DataFrame(sens).to_csv(MIDDLE / "eip_threshold_sensitivity_v2.csv", index=False, encoding="utf-8-sig")
    print("sensitivity grid done", flush=True)

    rec_ok = pool[pass_flags(pool, config.RECOMMENDED_FULL_TRADES, config.RECOMMENDED_FROZEN_TRADES)].copy()
    rec_ok["abs_full_avg"] = rec_ok["full_avg"].abs()
    rec_ok = rec_ok.sort_values(["abs_full_avg","frozen_hit","full_hit","frozen_trades"], ascending=False)
    if name_map:
        rec_ok["fund_name"] = rec_ok["ticker"].map(name_map)
    rec_ok.to_csv(MIDDLE / "eip_single_baseline_pass_v2.csv", index=False, encoding="utf-8-sig")
    best_rec = best_per_fund(rec_ok)
    if name_map:
        best_rec["fund_name"] = best_rec["ticker"].map(name_map)
    best_rec.to_csv(MIDDLE / "eip_single_best_strategy_v2.csv", index=False, encoding="utf-8-sig")
    covered = set(best_rec["ticker"]) if len(best_rec) else set()
    uncovered = sorted(set(fund_cols) - covered)
    if uncovered:
        pd.DataFrame({"isin": uncovered, "fund_name": [name_map.get(i, "") for i in uncovered]}).to_csv(
            MIDDLE / "eip_uncovered_v2.csv", index=False, encoding="utf-8-sig")
    print("recommended pass signals:", len(rec_ok), "covered funds:", len(covered), "uncovered:", len(uncovered), flush=True)
    sz = os.path.getsize(MIDDLE / "eip_single_pass_v2.csv")
    print("eip_single_pass_v2.csv bytes:", sz, "rows:", len(pool), flush=True)
    print("elapsed:", round(time.time()-t0, 1), "s", flush=True)

if __name__ == "__main__":
    main()