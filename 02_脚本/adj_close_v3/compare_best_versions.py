"""Compare all-ETF best vs streamlined best to explain hit-rate differences."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
ALL = ROOT / "最新成果" / "全部ETF" / "成果" / "每基金策略映射.xlsx"
STREAM = ROOT / "最新成果" / "精简ETF" / "成果" / "每基金策略映射.xlsx"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    all_df = pd.read_excel(ALL, sheet_name="数据")
    stream_df = pd.read_excel(STREAM, sheet_name="数据")
    print("all cols", list(all_df.columns))
    print("stream cols", list(stream_df.columns))
    all_df = all_df.rename(
        columns={
            "基金名称（代码）": "fund",
            "全历史平均回报（%）": "all_full_avg",
            "全历史命中率": "all_full_hit",
            "冻结期命中率": "all_frozen_hit",
            "冻结期平均回报（%）": "all_frozen_avg",
        }
    )
    stream_df = stream_df.rename(
        columns={
            "基金名称（代码）": "fund",
            "全历史平均回报（%）": "s_full_avg",
            "全历史命中率": "s_full_hit",
            "冻结期命中率": "s_frozen_hit",
            "冻结期平均回报（%）": "s_frozen_avg",
        }
    )
    merged = all_df[["fund", "all_full_avg", "all_full_hit", "all_frozen_hit", "all_frozen_avg"]].merge(
        stream_df[["fund", "s_full_avg", "s_full_hit", "s_frozen_hit", "s_frozen_avg"]],
        on="fund",
    )
    merged["frozen_diff"] = merged["s_frozen_hit"] - merged["all_frozen_hit"]
    merged["avg_diff"] = merged["all_full_avg"].abs() - merged["s_full_avg"].abs()
    changed = merged[merged["all_full_avg"] != merged["s_full_avg"]]
    worse = merged[merged["frozen_diff"] > 0]
    print("funds compared", len(merged))
    print("funds where best strategy changed", len(changed))
    print("funds where streamlined frozen hit > all-ETF frozen hit", len(worse))
    print("median frozen hit all", merged["all_frozen_hit"].median())
    print("median frozen hit stream", merged["s_frozen_hit"].median())
    print()
    print("examples where stream frozen hit higher but all avg higher:")
    examples = worse[worse["avg_diff"] > 0].sort_values("frozen_diff", ascending=False).head(10)
    print(
        examples[
            [
                "fund",
                "all_full_avg",
                "s_full_avg",
                "all_frozen_hit",
                "s_frozen_hit",
                "all_full_hit",
                "s_full_hit",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
