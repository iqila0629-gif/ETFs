"""Build delivery-preview key outputs for the streamlined 14-ETF version."""

from __future__ import annotations

import pathlib
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
EVENT = ROOT.parent / "event_study"
DELIV = ROOT / "delivery_preview"
SRC = ROOT / "etf_streamline_formal"
OUT = DELIV / "精简ETF" / "成果"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVENT))

from run_etf_streamline import build_signal_requirements, load_pool  # noqa: E402
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


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    (OUT / "正式预测_最佳策略_全历史").mkdir(parents=True, exist_ok=True)
    (OUT / "正式预测_最佳策略_冻结期").mkdir(parents=True, exist_ok=True)

    pool = load_pool()
    etfs = [str(e) for e in pd.read_csv(DELIV / "全部ETF" / "成果" / "v3_ETF使用统计.csv")["ETF"]]
    selected = [str(e) for e in pd.read_csv(SRC / "etf_streamlined_list.csv")["ETF"]]
    req_lo, req_hi = build_signal_requirements(pool, etfs)
    selected_bits = sum(1 << i for i, e in enumerate(etfs) if e in set(selected))
    mask64 = (1 << 64) - 1
    sel_lo = selected_bits & mask64
    sel_hi = selected_bits >> 64
    avail = ((req_lo & np.uint64(mask64 ^ sel_lo)) == 0) & (
        (req_hi & np.uint64(mask64 ^ sel_hi)) == 0
    )
    avail_pool = pool[avail].reset_index(drop=True)
    avail_pool.to_csv(OUT / "正式信号_全量.csv", index=False)

    shutil.copy2(SRC / "etf_streamlined_best_strategies.csv", OUT / "每基金最佳策略.csv")
    shutil.copy2(SRC / "etf_streamlined_signal_detail.csv", OUT / "信号逐日明细_最佳策略.csv")
    shutil.copy2(SRC / "etf_streamlined_company_full_history.csv", OUT / "公司格式_最佳策略_全历史.csv")
    shutil.copy2(SRC / "etf_streamlined_company_frozen.csv", OUT / "公司格式_最佳策略_冻结期.csv")
    shutil.copy2(SRC / "etf_streamlined_options.csv", OUT / "ETF规模影响_可选清单.csv")
    shutil.copy2(SRC / "etf_streamlined_报告.md", OUT / "精简报告.md")
    pd.DataFrame({"ETF": selected}).to_csv(OUT / "ETF列表.csv", index=False)

    best = pd.read_csv(OUT / "每基金最佳策略.csv")
    panel = pd.read_csv(EVENT / "panel_fund_returns_adj.csv")
    if "date" in panel.columns:
        panel = panel.rename(columns={"date": "Date"})
    all_tickers = list(panel.columns[1:])
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

    usage = []
    for e in selected:
        has = avail_pool["condition"].apply(lambda c: e in str(c).split("_"))
        best_has = best["condition"].apply(lambda c: e in str(c).split("_"))
        usage.append(
            {
                "ETF": e,
                "all_signals": int(has.sum()),
                "all_funds": int(avail_pool.loc[has, "ticker"].nunique()),
                "best_signals": int(best_has.sum()),
                "best_funds": int(best.loc[best_has, "ticker"].nunique()),
            }
        )
    pd.DataFrame(usage).sort_values(["all_signals", "all_funds"], ascending=False).to_csv(
        OUT / "ETF使用统计.csv", index=False
    )

    master = build_master()
    all_etfs = set(etfs)
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
    pd.DataFrame(detail).to_csv(OUT / "信号逐日明细_最佳策略_复核.csv", index=False)
    write_wide(OUT / "公司格式_最佳策略_全历史_复核.csv", dates_desc, all_tickers, by_fund)
    frozen = {
        t: {d: v for d, v in m.items() if d >= pd.Timestamp(CUTOFF)}
        for t, m in by_fund.items()
    }
    write_wide(
        OUT / "公司格式_最佳策略_冻结期_复核.csv",
        [d for d in dates_desc if d >= pd.Timestamp(CUTOFF)],
        all_tickers,
        frozen,
    )

    print("streamlined signals", len(avail_pool), "best funds", len(best))
    print("saved to", OUT)


if __name__ == "__main__":
    main()
