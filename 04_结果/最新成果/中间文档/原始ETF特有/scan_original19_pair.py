"""Exhaustive pairwise scan restricted to the original 19 ETFs (Adj Close)."""

from __future__ import annotations

import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

from expand_pair_scan import walk_forward_stats
from run_v3 import build_master_v3, ORIGINAL19


ROOT = pathlib.Path(__file__).resolve().parent
EVENT = ROOT.parent / "event_study"
CUTOFF = np.datetime64("2025-01-01")
HORIZONS = [1, 2, 3]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master = build_master_v3()
    fund_cols = [c for c in master.columns if c in set(pd.read_csv(EVENT / "panel_fund_returns_adj.csv").columns[1:])]
    etf_cols = [c for c in master.columns if c in ORIGINAL19]
    dates = master["Date"].to_numpy()
    fund_pct = master[fund_cols].to_numpy(dtype=float) * 100.0
    etf = {c: master[c].to_numpy(dtype=float) for c in etf_cols}

    pairs = list(itertools.combinations(etf_cols, 2))
    dirs = [
        ("up", "up", lambda a, b: (a > 0) & (b > 0)),
        ("down", "down", lambda a, b: (a < 0) & (b < 0)),
        ("up", "down", lambda a, b: (a > 0) & (b < 0)),
        ("down", "up", lambda a, b: (a < 0) & (b > 0)),
    ]
    rows = []
    for pi, (a, b) in enumerate(pairs):
        A, B = etf[a], etf[b]
        for da, db, mk in dirs:
            mask = mk(A, B)
            name = f"{a}_{da}_{b}_{db}"
            for h in HORIZONS:
                shifted = [np.roll(fund_pct, -k, axis=0) for k in range(1, h + 1)]
                target = np.mean(shifted, axis=0)
                target[-h:, :] = np.nan
                valid = mask[:, None] & np.isfinite(target)
                ev_count = valid.sum(axis=0)
                frozen_valid = valid & (dates[:, None] >= CUTOFF)
                frozen_count = frozen_valid.sum(axis=0)
                for fi, fund in enumerate(fund_cols):
                    if ev_count[fi] < 50 or frozen_count[fi] < 10:
                        continue
                    event_idx = np.flatnonzero(valid[:, fi])
                    vals = target[event_idx, fi]
                    st = walk_forward_stats(vals, dates[event_idx])
                    if st is None:
                        continue
                    st.update(
                        {
                            "ticker": fund,
                            "fund_group": "pair_scan",
                            "source": "pair_scan_original19",
                            "condition": name,
                            "horizon": h,
                            "original_pass": (
                                st["full_avg"] == st["full_avg"]
                                and abs(st["full_avg"]) >= 0.2
                                and st["full_trades"] >= 50
                            ),
                            "strict_pass": (
                                st["full_avg"] == st["full_avg"]
                                and abs(st["full_avg"]) >= 0.2
                                and st["full_trades"] >= 50
                                and st["full_hit"] > 0.55
                                and st["frozen_avg"] == st["frozen_avg"]
                                and abs(st["frozen_avg"]) >= 0.2
                                and st["frozen_trades"] >= 10
                                and st["frozen_hit"] >= 0.55
                            ),
                            "frozen_pass": (
                                st["full_avg"] == st["full_avg"]
                                and abs(st["full_avg"]) >= 0.2
                                and st["full_trades"] >= 50
                                and st["frozen_avg"] == st["frozen_avg"]
                                and abs(st["frozen_avg"]) >= 0.2
                                and st["frozen_trades"] >= 10
                                and st["frozen_hit"] >= 0.55
                            ),
                        }
                    )
                    rows.append(st)
        if (pi + 1) % 30 == 0:
            print(f"pairs done {pi+1}/{len(pairs)} rows {len(rows)}", flush=True)

    pool = pd.DataFrame(rows)
    pool.to_csv(ROOT / "original19_pair_candidates_stats.csv", index=False)
    pool[pool["original_pass"]].to_csv(ROOT / "original19_pair_original_pass.csv", index=False)
    pool[pool["strict_pass"]].to_csv(ROOT / "original19_pair_strict_pass.csv", index=False)
    pool[pool["frozen_pass"]].to_csv(ROOT / "original19_pair_frozen_pass.csv", index=False)
    print("pairs evaluated", len(pairs) * 4 * len(HORIZONS))
    print("original pass", int(pool["original_pass"].sum()), "funds", pool.loc[pool["original_pass"], "ticker"].nunique())
    print("strict pass", int(pool["strict_pass"].sum()), "funds", pool.loc[pool["strict_pass"], "ticker"].nunique())
    print("frozen pass", int(pool["frozen_pass"].sum()), "funds", pool.loc[pool["frozen_pass"], "ticker"].nunique())


if __name__ == "__main__":
    main()
