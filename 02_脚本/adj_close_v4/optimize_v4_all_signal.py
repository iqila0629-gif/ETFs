"""Test quality-filtered all-signal R4 merge (top-N by |full avg|)."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4
from build_v4_all_signal import merge_daily
from select_v4_strategies import signal_trades


def formal_pass(st: dict) -> bool:
    return bool(
        abs(st["full_avg"]) >= 0.2
        and st["full_trades"] >= config.RECOMMENDED_FULL_TRADES
        and st["full_hit"] > 0.55
        and st["frozen_avg"] == st["frozen_avg"]
        and abs(st["frozen_avg"]) >= 0.2
        and st["frozen_trades"] >= config.RECOMMENDED_FROZEN_TRADES
        and st["frozen_hit"] >= 0.55
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    fund_set = set(fund_cols)
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    dates = master["Date"].to_numpy()

    pool = pd.read_csv(config.V4_FINAL20_COMBINED_PASS, keep_default_na=False)
    pool["full_avg"] = pd.to_numeric(pool["full_avg"], errors="coerce")
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    fund_recs = {}
    for ticker, grp in pool.groupby("ticker", sort=True):
        recs = []
        for r in grp.itertuples(index=False):
            rec = signal_trades(
                master, dates, ticker, str(r.condition), int(r.horizon),
                str(r.source), all_etfs, target_cache,
            )
            if rec is not None:
                recs.append(rec)
        recs.sort(key=lambda s: -abs(s["full_avg"]))
        fund_recs[ticker] = recs
    print("funds with recs:", len(fund_recs), flush=True)

    N_list = [5, 10, 20, 50, 100, "all"]
    summary_rows = []
    for N in N_list:
        pass_count = 0
        avgs = []
        hits = []
        trades = []
        favgs = []
        fhits = []
        ftrades = []
        for ticker, recs in fund_recs.items():
            sel = recs if N == "all" else recs[:N]
            st, _ = merge_daily(sel)
            if formal_pass(st):
                pass_count += 1
            avgs.append(abs(st["full_avg"]))
            hits.append(st["full_hit"])
            trades.append(st["full_trades"])
            favgs.append(abs(st["frozen_avg"]))
            fhits.append(st["frozen_hit"])
            ftrades.append(st["frozen_trades"])
        summary_rows.append(
            {
                "N": str(N),
                "funds": len(fund_recs),
                "formal_pass": pass_count,
                "median_full_avg": round(float(np.median(avgs)), 4),
                "median_full_hit": round(float(np.median(hits)), 4),
                "median_full_trades": int(np.median(trades)),
                "median_frozen_avg": round(float(np.median(favgs)), 4),
                "median_frozen_hit": round(float(np.median(fhits)), 4),
                "median_frozen_trades": int(np.median(ftrades)),
            }
        )
        print("N", N, "pass", pass_count, "full_avg", round(float(np.median(avgs)),4), "hit", round(float(np.median(hits)),4), "trades", int(np.median(trades)), flush=True)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(config.V4_OUT / "v4_all_signal_topN_comparison.csv", index=False)
    print("saved comparison")


if __name__ == "__main__":
    main()
