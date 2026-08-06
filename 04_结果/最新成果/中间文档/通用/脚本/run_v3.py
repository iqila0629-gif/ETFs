"""Adj Close (total return) re-run: full pool, V1 19-ETF, V2 11-ETF."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测\analysis_results\event_study")))

import walk_forward as wf
from phase9_dual_criteria_pipeline import (
    CUTOFF,
    build_masks,
    get_mask,
    get_target,
)


ROOT = pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测")
EVENT = ROOT / "analysis_results" / "event_study"
OUT = ROOT / "analysis_results" / "adj_close_v3"
PROC = ROOT / "processed_returns"
ORIGINAL19 = {
    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP", "SLV",
    "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
}


def evaluate(mask, target, dates, min_n, min_p, min_abs):
    valid = mask.to_numpy(dtype=bool) & np.isfinite(target.to_numpy(dtype=float))
    ev_dates = dates.to_numpy()[valid]
    vals = target.to_numpy(dtype=float)[valid] * 100.0
    n = vals.size
    if n == 0:
        return ev_dates, vals, np.array([], dtype=bool)
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
    return ev_dates, vals, dec_up | dec_down


def build_master_v3():
    fund = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in fund.columns:
        fund = fund.rename(columns={"date": "Date"})
    etf19 = pd.read_csv(EVENT / "panel_etf_returns_adj.csv")
    ext57 = pd.read_csv(PROC / "combined_extended_etf_returns_adj.csv", skiprows=12)
    external = pd.read_csv(EVENT / "external_daily.csv", parse_dates=["Date"])
    keep = ["Date"] + [
        c
        for c in external.columns
        if c.startswith(("VIX", "TNX", "Credit", "JNK", "USD", "Sect", "Yld", "Stk"))
    ]
    external = external[keep]
    for df in (fund, etf19, ext57):
        df["Date"] = pd.to_datetime(df["Date"])
    master = (
        fund.merge(etf19, on="Date", how="left")
        .merge(ext57, on="Date", how="left")
        .merge(external, on="Date", how="left")
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return master


def stats_for(mask, target, dates, params):
    ev, vals, tm = evaluate(mask, target, dates, *params)
    td = ev[tm]
    tv = vals[tm]
    row = {
        "full_avg": float(tv.mean()) if td.size else float("nan"),
        "full_trades": int(td.size),
        "full_hit": float((tv > 0).mean()) if td.size else float("nan"),
        "frozen_avg": float("nan"),
        "frozen_trades": 0,
        "frozen_hit": float("nan"),
    }
    hold = td >= CUTOFF
    if hold.any():
        hv = tv[hold]
        row["frozen_avg"] = float(hv.mean())
        row["frozen_trades"] = int(hv.size)
        row["frozen_hit"] = float((hv > 0).mean())
    return row


def run_pool(candidates, master, masks, all_etfs, dates, label):
    rows = []
    for i, r in enumerate(candidates.itertuples(index=False)):
        ticker = str(r.ticker)
        condition = str(r.condition)
        horizon = int(r.horizon)
        source = str(r.source)
        params = (100, 0.55, 0.2) if source == "main" else (100, 0.52, 0.15)
        mask = get_mask(master, masks, ticker, condition, all_etfs)
        st = stats_for(mask, get_target(master, ticker, horizon), dates, params)
        st.update(
            {
                "ticker": ticker,
                "fund_group": r.fund_group,
                "source": source,
                "condition": condition,
                "horizon": horizon,
                "dual_pass": (
                    st["full_avg"] == st["full_avg"]
                    and abs(st["full_avg"]) >= 0.2
                    and st["full_trades"] >= 50
                    and st["full_hit"] > 0.55
                    and st["frozen_avg"] == st["frozen_avg"]
                    and abs(st["frozen_avg"]) >= 0.2
                    and st["frozen_trades"] >= 10
                    and st["frozen_hit"] >= 0.55
                ),
            }
        )
        rows.append(st)
        if (i + 1) % 3000 == 0:
            print(label, i + 1, "/", len(candidates), flush=True)
    return pd.DataFrame(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    master = build_master_v3()
    masks = build_masks(master)
    fund_cols = set(pd.read_csv(EVENT / "panel_fund_returns_adj.csv").columns[1:])
    non_fund = {
        "Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp", "CreditSpread",
        "JNKSpread", "StkBonCorr", "USDGoldRatio", "SectRotation", "VIX_5dChg",
        "VIX_20dVol", "VIX_TNX_Ratio", "YldCurveProxy",
    }
    all_etfs = {c for c in master.columns if c not in fund_cols and c not in non_fund}
    dates = master["Date"]

    candidates = pd.read_csv(EVENT / "dual_criteria_candidates.csv", keep_default_na=False)
    pool = run_pool(candidates, master, masks, all_etfs, dates, "v3-full")
    pool.to_csv(OUT / "v3_candidates_stats.csv", index=False)
    v3_pass = pool[pool["dual_pass"]].copy()
    v3_pass.to_csv(OUT / "v3_dual_criteria_pass.csv", index=False)

    best_rows = []
    for ticker, group in v3_pass.groupby("ticker"):
        row = group.sort_values(
            ["full_avg", "frozen_hit", "full_hit"],
            key=lambda s: s.abs() if s.name == "full_avg" else s,
            ascending=[False, False, False],
        ).iloc[0]
        best_rows.append(row)
    summary = pd.DataFrame(best_rows).sort_values("ticker").reset_index(drop=True)
    summary.to_csv(OUT / "v3_summary.csv", index=False)
    summary.to_csv(OUT / "v3_strategy_mapping.csv", index=False)

    def etf_tokens(cond):
        return [t for t in str(cond).split("_") if t in all_etfs]

    v1_candidates = candidates[
        candidates["condition"].apply(lambda c: all(t in ORIGINAL19 for t in etf_tokens(c)))
    ]
    v1_pool = run_pool(v1_candidates, master, masks, all_etfs, dates, "v1-19etf")
    v1_pass = v1_pool[v1_pool["dual_pass"]]
    v1_pass.to_csv(OUT / "v1_adj_pass.csv", index=False)

    v2_candidates = pd.read_csv(
        ROOT / "analysis_results" / "etf_streamline" / "streamlined_dual_criteria_pass.csv",
        keep_default_na=False,
    )[["ticker", "fund_group", "source", "condition", "horizon"]]
    v2_pool = run_pool(v2_candidates, master, masks, all_etfs, dates, "v2-11etf")
    v2_pass = v2_pool[v2_pool["dual_pass"]]
    v2_pass.to_csv(OUT / "v2_adj_pass.csv", index=False)

    old = pd.read_csv(ROOT / "analysis_results" / "standard_v2" / "v2_dual_criteria_pass.csv", keep_default_na=False)
    print("OLD close: signals", len(old), "funds", old["ticker"].nunique())
    print("V3 adj  : signals", len(v3_pass), "funds", v3_pass["ticker"].nunique())
    print("V1 adj  : signals", len(v1_pass), "funds", v1_pass["ticker"].nunique())
    print("V2 adj  : signals", len(v2_pass), "funds", v2_pass["ticker"].nunique())
    print("saved to", OUT)


if __name__ == "__main__":
    main()
