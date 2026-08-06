"""Convert processed data CSVs in 最新成果 to Excel with 说明/数据 sheets."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis_results" / "adj_close_v3"))

from build_final_delivery import (  # noqa: E402
    COMMON_COLMAP,
    write_company,
    write_plain,
)


DST = ROOT / "最新成果" / "数据" / "数据_处理后合并"


def main() -> None:
    jobs = [
        ("合并_基金Adj净值.csv", "合并_基金Adj净值.xlsx", True),
        ("合并_基金Adj日回报.csv", "合并_基金Adj日回报.xlsx", True),
        ("合并_ETF日回报_原始19支.csv", "合并_ETF日回报_原始19支.xlsx", False),
        ("合并_ETF日回报_扩展57支.csv", "合并_ETF日回报_扩展57支.xlsx", False),
    ]
    for src_name, out_name, display_funds in jobs:
        explain = [
            f"本表：{src_name.replace('.csv','')}。",
            "",
            "数据Sheet = 公司13行格式：",
            "第2-10行为统计公式；第13行为日期+标的；数据行从第14行开始。",
            "基金表每列为基金名称（代码），ETF表每列为ETF代码。",
        ]
        write_company(
            DST / src_name,
            DST / out_name,
            explain,
            display_funds=display_funds,
        )

    external_cols = {
        "Date": "日期",
        "SPY": "SPY",
        "VIX_Close": "VIX收盘",
        "VIX_Chg%": "VIX变化%",
        "TNX_Yield": "美债利率",
        "TNX_ChgBp": "美债变化(bp)",
        "CreditSpread": "信用利差",
        "JNKSpread": "高收益利差",
        "StkBonCorr": "股债相关性",
        "USDGoldRatio": "美元黄金比",
        "SectRotation": "板块轮动",
        "VIX_5dChg": "VIX5日变化",
        "VIX_20dVol": "VIX20日波动",
        "VIX_TNX_Ratio": "VIX/美债比",
        "YldCurveProxy": "收益率曲线代理",
    }
    write_plain(
        DST / "外部数据_VIX_TNX_未经处理.csv",
        DST / "外部数据_VIX_TNX_未经处理.xlsx",
        ["本表：VIX/TNX外部数据。", "", "仅做日期对齐，未按公司格式统计。"],
        external_cols,
    )
    write_plain(
        ROOT / "最新成果" / "数据" / "基金名称映射.csv",
        ROOT / "最新成果" / "数据" / "基金名称映射.xlsx",
        ["本表：ProFunds基金代码到名称的映射。", "", "每行 = 一支基金。"],
        {"ticker": "基金代码", "name": "基金名称"},
    )

    for name in [
        "合并_基金Adj净值.csv",
        "合并_基金Adj日回报.csv",
        "合并_ETF日回报_原始19支.csv",
        "合并_ETF日回报_扩展57支.csv",
        "外部数据_VIX_TNX_未经处理.csv",
    ]:
        (DST / name).unlink(missing_ok=True)
    (ROOT / "最新成果" / "数据" / "基金名称映射.csv").unlink(missing_ok=True)
    print("processed data converted")


if __name__ == "__main__":
    main()
