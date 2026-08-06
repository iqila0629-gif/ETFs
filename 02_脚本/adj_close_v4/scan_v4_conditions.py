"""v4 condition-type expansion: external, self, composite, 5/10-day windows."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
from scan_v4_triple import build_target, evaluate_mask


CUTOFF = np.datetime64("2025-01-01")
FULL_MIN = config.RECOMMENDED_FULL_TRADES
FROZEN_MIN = config.RECOMMENDED_FROZEN_TRADES
RAW_EVENT_MIN = FULL_MIN + 100
MIN_ABS_AVG = 0.2
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55
HORIZONS = [1, 2, 3, 5, 10]
DECISION_N = 100
DECISION_P = 0.52
DECISION_ABS = 0.15

EXTERNAL_COLS = {
    "vix_close": "VIX_Close",
    "vix_chg": "VIX_Chg%",
    "tnx_yield": "TNX_Yield",
    "tnx_chgbp": "TNX_ChgBp",
    "vix_5dchg": "VIX_5dChg",
    "vix_20dvol": "VIX_20dVol",
    "credit_spread": "CreditSpread",
    "jnk_spread": "JNKSpread",
    "stk_bon_corr": "StkBonCorr",
    "usd_gold_ratio": "USDGoldRatio",
    "sect_rotation": "SectRotation",
    "vix_tnx_ratio": "VIX_TNX_Ratio",
    "yld_curve_proxy": "YldCurveProxy",
}


def external_ops(col_name: str) -> list[tuple[str, float]]:
    ops = [("up", 0.0), ("down", 0.0)]
    if col_name in ("VIX_Close",):
        ops += [("ge25", 25.0), ("le15", 15.0)]
    if col_name in ("VIX_Chg%", "TNX_ChgBp"):
        ops += [("ge10", 10.0), ("le-10", -10.0)]
    if col_name in ("VIX_5dChg",):
        ops += [("ge10", 10.0), ("le-10", -10.0)]
    if col_name in ("VIX_20dVol",):
        ops += [("ge20", 20.0), ("le-20", -20.0)]
    if col_name in ("CreditSpread", "JNKSpread", "SectRotation", "YldCurveProxy"):
        ops += [("ge0_5", 0.5), ("le-0_5", -0.5)]
    if col_name in ("USDGoldRatio", "VIX_TNX_Ratio", "StkBonCorr", "TNX_Yield"):
        ops += [("ge1", 1.0), ("le-1", -1.0)]
    return ops


def build_external_conditions() -> list[str]:
    out = []
    for safe, col in EXTERNAL_COLS.items():
        for op, _ in external_ops(col):
            out.append(f"ext_{safe}_{op}")
    return out


def build_self_conditions() -> list[str]:
    return [
        "self_up",
        "self_down",
        "self_big_up",
        "self_big_down",
        "self_3up",
        "self_3down",
        "self_5up",
        "self_5down",
    ]


def build_etf_conditions() -> list[str]:
    out = []
    for etf in sorted(config.ORIGINAL19):
        for suffix in ["up", "down", "big_up", "big_down", "gt2", "lt-2"]:
            out.append(f"{etf}_{suffix}")
    return out


def build_composite_conditions() -> list[str]:
    ext = build_external_conditions()
    selfs = build_self_conditions()
    etfs = [c for c in build_etf_conditions() if c.split("_")[-1] in {"up", "down", "big_up", "big_down"}]
    out = []
    for e in etfs:
        for x in ext:
            out.append(f"combo_{e}__{x}")
        for s in selfs:
            out.append(f"combo_{e}__{s}")
    for x in ext:
        for s in selfs:
            out.append(f"combo_{x}__{s}")
    return out


def build_single_mask(master: pd.DataFrame, name: str, ticker: str) -> pd.Series:
    if name.startswith("ext_"):
        safe = None
        op = None
        for candidate, col in EXTERNAL_COLS.items():
            prefix = f"ext_{candidate}_"
            if name.startswith(prefix):
                safe = candidate
                op = name[len(prefix):]
                break
        if safe is None or op is None:
            raise ValueError(name)
        col = EXTERNAL_COLS[safe]
        s = master[col].to_numpy(dtype=float)
        if op == "up":
            return pd.Series(s > 0, index=master.index)
        if op == "down":
            return pd.Series(s < 0, index=master.index)
        threshold = float(op[2:].replace("_", "."))
        if op.startswith("ge"):
            return pd.Series(s >= threshold, index=master.index)
        return pd.Series(s <= threshold, index=master.index)
    if name.startswith("self_"):
        r = master[ticker]
        suffix = name.removeprefix("self_")
        if suffix == "up":
            return r > 0
        if suffix == "down":
            return r < 0
        if suffix == "big_up":
            return r >= 0.02
        if suffix == "big_down":
            return r <= -0.02
        if suffix == "3up":
            return (r > 0) & (r.shift(1) > 0) & (r.shift(2) > 0)
        if suffix == "3down":
            return (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0)
        if suffix == "5up":
            return (r > 0) & (r.shift(1) > 0) & (r.shift(2) > 0) & (r.shift(3) > 0) & (r.shift(4) > 0)
        if suffix == "5down":
            return (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0) & (r.shift(3) < 0) & (r.shift(4) < 0)
        raise ValueError(name)
    tokens = name.split("_")
    etf = tokens[0]
    suffix = "_".join(tokens[1:])
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
    raise ValueError(name)


def build_mask(master: pd.DataFrame, condition: str, ticker: str) -> pd.Series:
    if condition.startswith("combo_"):
        p1, p2 = condition[len("combo_"):].split("__")
        return build_single_mask(master, p1, ticker) & build_single_mask(master, p2, ticker)
    return build_single_mask(master, condition, ticker)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config.V4_OUT.mkdir(parents=True, exist_ok=True)

    master = None
    from scan_v4_thresholds import load_master as load_base_master
    master = load_base_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    dates = master["Date"].to_numpy()
    fund_arr = master[fund_cols].to_numpy(dtype=float)
    targets = {h: build_target(fund_arr, h) for h in HORIZONS}

    conditions = (
        build_external_conditions()
        + build_self_conditions()
        + build_composite_conditions()
    )
    conditions = list(dict.fromkeys(conditions))
    print("condition count:", len(conditions), "horizons", HORIZONS, flush=True)

    pass_rows = []
    checked = 0
    for ci, condition in enumerate(conditions, start=1):
        if "self_" in condition:
            masks = {
                fi: build_mask(master, condition, fund_cols[fi]).to_numpy(dtype=bool)
                for fi in range(len(fund_cols))
            }
        else:
            base = build_mask(master, condition, fund_cols[0]).to_numpy(dtype=bool)
            masks = {fi: base for fi in range(len(fund_cols))}
        for horizon in HORIZONS:
            target = targets[horizon]
            tickers_eligible = []
            for fi, ticker in enumerate(fund_cols):
                mask = masks[fi]
                valid = mask & np.isfinite(target[:, fi])
                if valid.sum() < RAW_EVENT_MIN or (valid & (dates >= CUTOFF)).sum() < FROZEN_MIN:
                    continue
                tickers_eligible.append(fi)
            for fi in tickers_eligible:
                ticker = fund_cols[fi]
                mask = masks[fi]
                ev_dates, vals, trade_mask = evaluate_mask(
                    mask, target[:, fi], dates, DECISION_N, DECISION_P, DECISION_ABS
                )
                if not trade_mask.any():
                    continue
                td = ev_dates[trade_mask]
                tv = vals[trade_mask]
                if td.size < FULL_MIN or int((td >= CUTOFF).sum()) < FROZEN_MIN:
                    continue
                hold = td >= CUTOFF
                full_avg = float(tv.mean())
                full_trades = int(tv.size)
                full_hit = float((tv > 0).mean())
                frozen_avg = float(tv[hold].mean()) if hold.any() else float("nan")
                frozen_trades = int(hold.sum())
                frozen_hit = float((tv[hold] > 0).mean()) if hold.any() else float("nan")
                is_pass = bool(
                    abs(full_avg) >= MIN_ABS_AVG
                    and full_trades >= FULL_MIN
                    and full_hit > MIN_FULL_HIT
                    and frozen_avg == frozen_avg
                    and abs(frozen_avg) >= MIN_ABS_AVG
                    and frozen_trades >= FROZEN_MIN
                    and frozen_hit >= MIN_FROZEN_HIT
                )
                if is_pass:
                    pass_rows.append(
                        {
                            "ticker": ticker,
                            "source": "condition_expansion",
                            "condition": condition,
                            "horizon": horizon,
                            "full_avg": full_avg,
                            "full_trades": full_trades,
                            "full_hit": full_hit,
                            "frozen_avg": frozen_avg,
                            "frozen_trades": frozen_trades,
                            "frozen_hit": frozen_hit,
                        }
                    )
            checked += 1
        if ci % 200 == 0:
            print(f"conditions {ci}/{len(conditions)} pass={len(pass_rows)}", flush=True)

    out = pd.DataFrame(pass_rows)
    out.to_csv(config.V4_OUT / "v4_condition_expansion_pass.csv", index=False)
    print("checked:", checked, "pass rows:", len(out), "funds:", out["ticker"].nunique() if len(out) else 0)


if __name__ == "__main__":
    main()
