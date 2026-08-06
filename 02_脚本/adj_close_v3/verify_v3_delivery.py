"""Read-only QA for the restructured delivery preview (three versions)."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "delivery_preview"

sys.path.insert(0, str(ROOT.parent / "event_study"))
sys.path.insert(0, str(ROOT))

from build_v3_delivery import (  # noqa: E402
    CUTOFF,
    build_master,
    evaluate_signal,
    get_target,
    params_for,
)


def check_best_consistency(folder: pathlib.Path, best: pd.DataFrame, master, dates, cache: dict, all_etfs: set[str]):
    max_diff = 0.0
    bad = 0
    for _, row in best.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        source = str(row["source"])
        key = (condition, ticker if condition.startswith("self_") else None)
        if key not in cache:
            from build_v3_delivery import build_condition_mask
            cache[key] = build_condition_mask(master, condition, ticker, all_etfs)
        mask = cache[key]
        target = get_target(master, ticker, horizon, strict_finite=source.startswith("pair_scan"))
        ev_dates, vals, tm, _ = evaluate_signal(mask, target, dates, *params_for(source))
        if not tm.any():
            bad += 1
            continue
        tv = vals[tm]
        diff = abs(float(tv.mean()) - float(row["full_avg"]))
        max_diff = max(max_diff, diff)
        if diff > 1e-8:
            bad += 1
    return max_diff, bad


def check_wide(folder: pathlib.Path, full_name: str, frozen_name: str, min_full_trades: int):
    full = pd.read_csv(folder / full_name, skiprows=12)
    frozen = pd.read_csv(folder / frozen_name, skiprows=12)
    full_ok = 0
    frozen_ok = 0
    for col in full.columns[1:]:
        vals = full[col].dropna()
        if vals.empty:
            continue
        if abs(vals.mean()) >= 0.2 and len(vals) >= min_full_trades and (vals > 0).mean() >= 0.55:
            full_ok += 1
    for col in frozen.columns[1:]:
        vals = frozen[col].dropna()
        if vals.empty:
            continue
        if abs(vals.mean()) >= 0.2 and len(vals) >= 10 and (vals > 0).mean() >= 0.55:
            frozen_ok += 1
    return full_ok, frozen_ok


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master = build_master()
    dates = master["Date"].to_numpy()
    cache: dict[tuple[str, str | None], pd.Series] = {}
    fund_cols = set(pd.read_csv(ROOT.parent / "event_study" / "panel_fund_returns_adj.csv").columns[1:])
    all_etfs = {
        c for c in master.columns if c not in fund_cols and c not in {
            "Date", "VIX_Close", "VIX_Chg%", "TNX_Yield", "TNX_ChgBp",
            "CreditSpread", "JNKSpread", "StkBonCorr", "USDGoldRatio",
            "SectRotation", "VIX_5dChg", "VIX_20dVol", "VIX_TNX_Ratio",
            "YldCurveProxy",
        }
    }

    jobs = [
        (
            "全部ETF",
            OUT / "全部ETF" / "成果",
            "v3_正式信号_全量.csv",
            "v3_每基金最佳策略.csv",
            "v3_公司格式_最佳策略_全历史.csv",
            "v3_公司格式_最佳策略_冻结期.csv",
            50,
        ),
        (
            "精简ETF",
            OUT / "精简ETF" / "成果",
            "正式信号_全量.csv",
            "每基金最佳策略.csv",
            "公司格式_最佳策略_全历史.csv",
            "公司格式_最佳策略_冻结期.csv",
            50,
        ),
        (
            "原始ETF",
            OUT / "原始ETF" / "成果",
            "正式信号_全量.csv",
            "每基金最佳策略.csv",
            "公司格式_最佳策略_全历史.csv",
            "公司格式_最佳策略_冻结期.csv",
            50,
        ),
    ]

    for label, folder, signals_name, best_name, full_name, frozen_name, min_trades in jobs:
        pool = pd.read_csv(folder / signals_name, keep_default_na=False)
        best = pd.read_csv(folder / best_name, keep_default_na=False)
        print(label, "signals", len(pool), "best", len(best), "unique", best["ticker"].nunique())
        print(label, "dup keys", int(pool.duplicated(["ticker", "condition", "horizon"]).sum()))
        print(label, "best dup tickers", int(best["ticker"].duplicated().sum()))
        max_diff, bad = check_best_consistency(folder, best, master, dates, cache, all_etfs)
        print(label, "best avg max diff", round(max_diff, 10), "bad", bad)
        full_ok, frozen_ok = check_wide(folder, full_name, frozen_name, min_trades)
        print(label, "full wide ok", full_ok, "frozen wide ok", frozen_ok)

    for p in [
        OUT / "精简ETF" / "影响说明.txt",
        OUT / "全部ETF" / "说明.txt",
        OUT / "原始ETF" / "说明.txt",
        OUT / "总说明.txt",
        OUT / "文件说明.txt",
        OUT / "预测逻辑.txt",
    ]:
        print("doc exists", p.name, p.exists())


if __name__ == "__main__":
    main()
