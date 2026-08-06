"""Rebuild merged xlsx from adjusted-close CSVs."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import rename_and_add_sheets as ras


ROOT = pathlib.Path(r"C:\Users\vanessacen\Desktop\基金预测")
PROC = ROOT / "processed_returns"

JOBS = [
    (PROC / "combined_profunds_adj_nav.csv", "合并_基金净值_129支.xlsx",
     ["本表：129 支基金 Adjusted Close（总回报口径）合并表。",
      "2026-08-05 更新：数据来自 Nasdaq assetclass=mutualfunds 的 Adjusted Close，",
      "已包含基金分红/资本利得再投资调整。",
      "第 13 行为 Date + 基金代码；数据行为每日 Adjusted NAV。"]),
    (PROC / "combined_etf_returns_adj.csv", "合并_ETF日回报_原始19支.xlsx",
     ["本表：原始 19 支 ETF 的 Adj Close 日回报（总回报口径）。",
      "2026-08-05 更新：使用 Yahoo 原始数据中的 Adj Close 计算，已含分红调整。",
      "第 13 行为 Date + ETF 代码；数据行为每日回报（%）。"]),
    (PROC / "combined_extended_etf_returns_adj.csv", "合并_ETF日回报_扩展57支.xlsx",
     ["本表：扩展 57 支 ETF 的 Adj Close 日回报（总回报口径）。",
      "2026-08-05 更新：数据来自 Yahoo v8 API 全新下载（raw_data/etfs_extended_full/），",
      "用 Adj Close 计算，已含分红调整，历史从各自上市日开始。",
      "第 13 行为 Date + ETF 代码；数据行为每日回报（%）。"]),
]

FOLDERS = [
    ROOT / "最终成果" / "数据" / "数据_处理后合并",
    ROOT / "失败版本" / "版本1_原始ETF列表_覆盖率不足" / "数据" / "数据_处理后合并",
    ROOT / "失败版本" / "版本2_ETF精简_命中率不足" / "数据" / "数据_处理后合并",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for folder in FOLDERS:
        for csv_path, name, explain in JOBS:
            ras.build_company13(csv_path, folder / name, explain)
            print("rebuilt", folder / name)


if __name__ == "__main__":
    main()
