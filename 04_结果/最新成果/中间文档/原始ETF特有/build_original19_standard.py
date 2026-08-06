"""Build standard-caliber key outputs for the original 19-ETF version."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
EVENT = ROOT.parent / "event_study"
DELIV = ROOT / "delivery_preview"
OUT = DELIV / "原始ETF" / "成果"

sys.path.insert(0, str(EVENT))

from build_v3_delivery import (  # noqa: E402
    CUTOFF,
    build_master,
    evaluate_signal,
    get_target,
    params_for,
    write_wide,
)
from event_metrics import fund_group  # noqa: E402
from generate_predictions import write_standard_csv  # noqa: E402


ORIGINAL19 = {
    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP", "SLV",
    "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    (OUT / "正式预测_最佳策略_全历史").mkdir(parents=True, exist_ok=True)
    (OUT / "正式预测_最佳策略_冻结期").mkdir(parents=True, exist_ok=True)

    old = pd.read_csv(ROOT / "v1_adj_pass.csv", keep_default_na=False)
    pair = pd.read_csv(ROOT / "original19_pair_strict_pass.csv", keep_default_na=False)
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
    pool = pd.concat([old[cols], pair[cols]], ignore_index=True)
    pool["fund_group"] = pool["ticker"].map(fund_group)
    for c in ["full_avg", "full_trades", "full_hit", "frozen_avg", "frozen_trades", "frozen_hit"]:
        pool[c] = pd.to_numeric(pool[c], errors="coerce")
    pool["abs_full_avg"] = pool["full_avg"].abs()
    pool = pool.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
        ascending=False,
    )
    pool = pool.drop_duplicates(["ticker", "condition", "horizon"], keep="first")
    pool = pool.sort_values("ticker").reset_index(drop=True)
    pool.to_csv(OUT / "正式信号_全量.csv", index=False)

    best = pool.sort_values(
        ["abs_full_avg", "frozen_hit", "full_hit", "frozen_trades"],
        ascending=False,
    ).groupby("ticker", sort=True).head(1).sort_values("ticker").reset_index(drop=True)
    best["decision"] = np.where(best["full_avg"] > 0, "predict_up", "predict_down")
    best.to_csv(OUT / "每基金最佳策略.csv", index=False)

    master = build_master()
    panel = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in panel.columns:
        panel = panel.rename(columns={"date": "Date"})
    all_tickers = list(panel.columns[1:])
    fund_set = set(all_tickers)
    all_etfs = {
        c for c in master.columns if c not in fund_set and c not in {
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
    }
    dates = master["Date"].to_numpy()
    dates_desc = list(pd.to_datetime(master["Date"]).sort_values(ascending=False))
    by_fund: dict[str, dict[pd.Timestamp, float]] = {t: {} for t in all_tickers}
    detail: list[dict] = []
    cache: dict[tuple[str, str | None], pd.Series] = {}

    def mask_for(condition: str, ticker: str) -> pd.Series:
        key = (condition, ticker if condition.startswith("self_") else None)
        if key not in cache:
            from build_v3_delivery import build_condition_mask

            cache[key] = build_condition_mask(master, condition, ticker, all_etfs)
        return cache[key]

    for _, row in best.iterrows():
        ticker = str(row["ticker"])
        condition = str(row["condition"])
        horizon = int(row["horizon"])
        source = str(row["source"])
        mask = mask_for(condition, ticker)
        target = get_target(master, ticker, horizon, strict_finite=source.startswith("pair_scan"))
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
        write_standard_csv(OUT / "正式预测_最佳策略_全历史" / f"{name}.csv", full_rows)
        if frozen_rows:
            write_standard_csv(OUT / "正式预测_最佳策略_冻结期" / f"{name}.csv", frozen_rows)
        for d, v, pr in zip(td, tv, tp):
            by_fund[ticker][pd.Timestamp(d)] = float(v)
            detail.append(
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
    pd.DataFrame(detail).to_csv(OUT / "信号逐日明细_最佳策略.csv", index=False)
    write_wide(OUT / "公司格式_最佳策略_全历史.csv", dates_desc, all_tickers, by_fund)
    frozen = {
        t: {d: v for d, v in m.items() if d >= pd.Timestamp(CUTOFF)}
        for t, m in by_fund.items()
    }
    write_wide(
        OUT / "公司格式_最佳策略_冻结期.csv",
        [d for d in dates_desc if d >= pd.Timestamp(CUTOFF)],
        all_tickers,
        frozen,
    )

    covered = set(best["ticker"])
    coverage_rows = []
    for t in all_tickers:
        coverage_rows.append(
            {
                "ticker": t,
                "fund_group": fund_group(t),
                "covered": t in covered,
                "reason": "money_fund" if t in {"MPIXX", "MPSXX"} else ("covered" if t in covered else "not_qualified"),
            }
        )
    pd.DataFrame(coverage_rows).to_csv(OUT / "覆盖情况.csv", index=False)

    def etfs_in(condition: str) -> list[str]:
        return [t for t in condition.split("_") if t in ORIGINAL19]

    usage = []
    for e in sorted(ORIGINAL19):
        in_pool = pool[pool["condition"].apply(lambda c: e in etfs_in(c))]
        in_best = best[best["condition"].apply(lambda c: e in etfs_in(c))]
        usage.append(
            {
                "ETF": e,
                "in_best": bool(len(in_best)),
                "best_signals": len(in_best),
                "best_funds": int(in_best["ticker"].nunique()),
                "all_signals": len(in_pool),
                "all_funds": int(in_pool["ticker"].nunique()),
            }
        )
    pd.DataFrame(usage).sort_values(["all_signals", "all_funds"], ascending=False).to_csv(
        OUT / "ETF使用统计.csv", index=False
    )

    print("original19 standard signals", len(pool), "funds", pool["ticker"].nunique())
    print("best funds", len(best))
    print("saved to", OUT)


if __name__ == "__main__":
    main()
