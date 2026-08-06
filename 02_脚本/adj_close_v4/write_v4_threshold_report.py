"""Write the v4 threshold sensitivity report from scan outputs."""

from __future__ import annotations

import sys

import pandas as pd

import config


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sens = pd.read_csv(config.V4_OUT / "v4_threshold_sensitivity.csv", keep_default_na=False)
    best = pd.read_csv(config.V4_OUT / "v4_19etf_best_strategy.csv", keep_default_na=False)
    rec_full = config.RECOMMENDED_FULL_TRADES
    rec_frozen = config.RECOMMENDED_FROZEN_TRADES
    rec_row = sens[(sens["full_min_trades"].astype(int) == rec_full) & (sens["frozen_min_trades"].astype(int) == rec_frozen)]

    lines = [
        "# v4 门槛敏感性报告",
        "",
        "> 日期：2026-08-06",
        "> 数据范围：原始 19 支 ETF + VIX/TNX 外部数据 + 基金自身信号",
        "> 口径：walk-forward（无未来信息）+ 全历史/冻结期双口径",
        "",
        "## 一、扫描说明",
        "",
        f"- 候选池：v3 单条件 + 双条件严格池中，条件所需 ETF 全部在原始 19 支内的信号，去重后共 {len(pd.read_csv(config.V4_OUT / 'v4_19etf_recomputed_stats.csv'))} 条有效重算记录。",
        f"- 门槛网格：全历史交易数 {config.THRESHOLD_GRID_FULL}，冻结期交易数 {config.THRESHOLD_GRID_FROZEN}。",
        "- 其他门槛不变：全历史 `|Average| >= 0.2%`、命中率 `> 55%`；冻结期 `|Average| >= 0.2%`、命中率 `>= 55%`。",
        "",
        "## 二、敏感性总表",
        "",
        "| 全历史交易数 | 冻结期交易数 | 信号数 | 覆盖基金 | 未覆盖非货币 | 全历史Average中位数 | 全历史命中率中位数 | 全历史交易数中位数 | 冻结期Average中位数 | 冻结期命中率中位数 | 冻结期交易数中位数 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in sens.iterrows():
        vals = [
            r["median_full_avg_abs"],
            r["median_full_hit"],
            r["median_frozen_avg_abs"],
            r["median_frozen_hit"],
        ]
        rounded = [f"{float(v):.4f}" if v not in ("", None) and str(v) != "" else "" for v in vals]
        lines.append(
            f"| {int(r['full_min_trades'])} | {int(r['frozen_min_trades'])} | {r['signals']} | {r['covered_funds']} | {r['uncovered_non_money']} | {rounded[0]} | {rounded[1]} | {r['median_full_trades']} | {rounded[2]} | {rounded[3]} | {r['median_frozen_trades']} |"
        )

    lines += [
        "",
        "## 三、推荐门槛",
        "",
        f"- 推荐组合：全历史 `>= {rec_full}`、冻结期 `>= {rec_frozen}`。",
    ]
    if len(rec_row):
        r = rec_row.iloc[0]
        lines += [
            f"- 信号数：{r['signals']}",
            f"- 覆盖基金：{r['covered_funds']}",
            f"- 未覆盖非货币基金：{r['uncovered_non_money']}",
            f"- 未覆盖清单：{r['uncovered_list'] if r['uncovered_list'] else '无'}",
        ]
    if len(best):
        lines += [
            "",
            "## 四、每基金最佳策略（推荐门槛）",
            "",
            "见 `v4_19etf_best_strategy.csv`，统计口径为每支基金在推荐门槛下的最佳策略。",
        ]
    lines += [
        "",
        "## 五、注意事项",
        "",
        "1. 冻结期只有约 1.5 年，交易数 20-30 的信号仍有小样本风险。",
        "2. 当前候选池只覆盖原始 19 支 ETF；扩展 ETF 已备份停用。",
        "3. 提高门槛后若覆盖不足，进入 Phase 3 用三信号扫描和其他方法补缺口。",
        "",
    ]
    out = config.V4_OUT / "v4_门槛敏感性报告.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("saved:", out)


if __name__ == "__main__":
    main()
