"""Evaluate how many selected-strategy trades are overridden in R4 merge."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4
from select_v4_strategies import signal_trades


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

    suffix = sys.argv[1] if len(sys.argv) > 1 else "_density"
    mapping = pd.read_csv(config.V4_OUT / f"v4_strategy_mapping{suffix}.csv", keep_default_na=False)
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    strategy_rows = []
    fund_rows = []

    for ticker, grp in mapping.groupby("ticker", sort=True):
        recs = []
        for r in grp.sort_values("strategy_no").itertuples(index=False):
            rec = signal_trades(
                master, dates, ticker, str(r.condition), int(r.horizon),
                str(r.source), all_etfs, target_cache,
            )
            if rec is not None:
                rec["strategy_no"] = r.strategy_no
                recs.append(rec)
        if not recs:
            continue

        winner = {}
        for rec in recs:
            for d in rec["dates"]:
                cur = winner.get(d)
                if cur is None or rec["strength"] > cur["strength"]:
                    winner[d] = rec

        sum_trades = 0
        overlap_days = 0
        for rec in recs:
            trades = len(rec["dates"])
            win = sum(1 for d in rec["dates"] if winner.get(d) is rec)
            overridden = trades - win
            exclusive = sum(
                1 for d in rec["dates"]
                if sum(1 for other in recs if d in other["dates"]) == 1
            )
            sum_trades += trades
            overlap_days += trades - exclusive
            strategy_rows.append(
                {
                    "ticker": ticker,
                    "strategy_no": rec["strategy_no"],
                    "condition": rec["condition"],
                    "horizon": rec["horizon"],
                    "trades": trades,
                    "winner_days": win,
                    "overridden_days": overridden,
                    "exclusive_days": exclusive,
                    "swallowed_ratio": overridden / trades if trades else 0.0,
                    "exclusive_ratio": exclusive / trades if trades else 0.0,
                }
            )

        union_days = len(winner)
        weighted_swallowed = (
            sum(r["overridden_days"] for r in strategy_rows if r["ticker"] == ticker) / sum_trades
            if sum_trades
            else 0.0
        )
        gt50 = sum(
            1 for r in strategy_rows
            if r["ticker"] == ticker and r["swallowed_ratio"] > 0.5
        )
        fund_rows.append(
            {
                "ticker": ticker,
                "n_strategies": len(recs),
                "union_days": union_days,
                "sum_trades": sum_trades,
                "overlap_days": overlap_days,
                "avg_strategies_per_day": sum_trades / union_days if union_days else 0.0,
                "weighted_swallowed_ratio": weighted_swallowed,
                "strategies_swallowed_gt50": gt50,
            }
        )

    strategy_df = pd.DataFrame(strategy_rows)
    fund_df = pd.DataFrame(fund_rows)
    strategy_df.to_csv(config.V4_OUT / f"v4_conflict_loss_strategy{suffix}.csv", index=False)
    fund_df.to_csv(config.V4_OUT / f"v4_conflict_loss_fund{suffix}.csv", index=False)

    print("strategies:", len(strategy_df), "funds:", fund_df["ticker"].nunique())
    print("swallowed ratio medians: all", round(strategy_df["swallowed_ratio"].median(), 3),
          ">30%:", int((strategy_df["swallowed_ratio"] > 0.3).sum()),
          ">50%:", int((strategy_df["swallowed_ratio"] > 0.5).sum()))
    print("exclusive ratio median:", round(strategy_df["exclusive_ratio"].median(), 3),
          "exclusive=0 strategies:", int((strategy_df["exclusive_days"] == 0).sum()))
    print("fund weighted swallowed median:", round(fund_df["weighted_swallowed_ratio"].median(), 3),
          "funds with any >50% strategy:", int((fund_df["strategies_swallowed_gt50"] > 0).sum()))
    print(fund_df.sort_values("weighted_swallowed_ratio", ascending=False).head(15).to_string(index=False))


if __name__ == "__main__":
    main()
