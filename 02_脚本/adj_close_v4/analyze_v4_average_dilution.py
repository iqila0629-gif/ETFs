"""Analyze marginal average contribution of added strategies."""

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
    suffix = sys.argv[1] if len(sys.argv) > 1 else "_complement"

    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    fund_set = set(fund_cols)
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in fund_set and c not in non_fund}
    dates = master["Date"].to_numpy()

    mapping = pd.read_csv(config.V4_OUT / f"v4_strategy_mapping{suffix}.csv", keep_default_na=False)
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    rows = []

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
        current = set()
        for idx, rec in enumerate(recs):
            new_dates = rec["dates"] - current
            if new_dates:
                marginal_avg = float(np.mean([rec["returns"][d] for d in new_dates]))
            else:
                marginal_avg = float("nan")
            rows.append(
                {
                    "ticker": ticker,
                    "strategy_no": rec["strategy_no"],
                    "condition": rec["condition"],
                    "own_avg": rec["full_avg"],
                    "new_dates": len(new_dates),
                    "marginal_avg": marginal_avg,
                }
            )
            current |= rec["dates"]

    df = pd.DataFrame(rows)
    df.to_csv(config.V4_OUT / f"v4_average_dilution{suffix}.csv", index=False)
    added = df[df["strategy_no"] > 1]
    print("version", suffix, "strategies", len(df), "added", len(added))
    print("anchor own avg median:", round(df.loc[df["strategy_no"] == 1, "own_avg"].abs().median(), 4))
    print("added marginal avg median:", round(added["marginal_avg"].abs().median(), 4))
    print("added marginal avg <0.2:", int((added["marginal_avg"].abs() < 0.2).sum()), "/", len(added))
    print("added marginal avg <0.3:", int((added["marginal_avg"].abs() < 0.3).sum()), "/", len(added))
    print("added marginal avg >0.5:", int((added["marginal_avg"].abs() > 0.5).sum()), "/", len(added))
    print(added.sort_values("marginal_avg").head(10).to_string(index=False))


if __name__ == "__main__":
    main()
