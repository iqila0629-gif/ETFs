"""Exhaustive pairwise ETF condition scan (all 76 ETFs, 1/2/3-day)."""

from __future__ import annotations

import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测\analysis_results\event_study")))

from run_v3 import build_master_v3


ROOT = pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测")
EVENT = ROOT / "analysis_results" / "event_study"
OUT = ROOT / "analysis_results" / "adj_close_v3"
CUTOFF = np.datetime64("2025-01-01")
HORIZONS = [1, 2, 3]


def walk_forward_stats(vals: np.ndarray, dates: np.ndarray):
    n = vals.size
    if n == 0:
        return None
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
        dec_up = (cum_n >= 100) & (p_up >= 0.52) & (avg_up >= 0.15)
        dec_down = (cum_n >= 100) & (p_down >= 0.52) & (avg_down <= -0.15)
    tm = dec_up | dec_down
    td = dates[tm]
    tv = vals[tm]
    if not td.size:
        return None
    row = {
        "full_avg": float(tv.mean()),
        "full_trades": int(td.size),
        "full_hit": float((tv > 0).mean()),
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


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master = build_master_v3()
    fund_cols = [c for c in master.columns if c in set(pd.read_csv(EVENT / "panel_fund_returns_adj.csv").columns[1:])]
    etf_cols = [
        c
        for c in master.columns
        if c not in set(fund_cols) | {
            "Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp", "CreditSpread",
            "JNKSpread", "StkBonCorr", "USDGoldRatio", "SectRotation", "VIX_5dChg",
            "VIX_20dVol", "VIX_TNX_Ratio", "YldCurveProxy",
        }
    ]
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
    checked = 0
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
                            "source": "pair_scan",
                            "condition": name,
                            "horizon": h,
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
                checked += 1
        if (pi + 1) % 200 == 0:
            print(f"pairs done {pi+1}/{len(pairs)} rows {len(rows)}", flush=True)

    pool = pd.DataFrame(rows)
    pool.to_csv(OUT / "pair_candidates_stats.csv", index=False)
    strict = pool[pool["strict_pass"]]
    frozen = pool[pool["frozen_pass"]]
    strict.to_csv(OUT / "pair_strict_pass.csv", index=False)
    frozen.to_csv(OUT / "pair_frozen_pass.csv", index=False)
    print("pair combos evaluated:", checked)
    print("strict pass:", len(strict), "funds", strict["ticker"].nunique())
    print("frozen pass:", len(frozen), "funds", frozen["ticker"].nunique())


if __name__ == "__main__":
    main()
