# -*- coding: utf-8 -*-
"""Generate the manual-download task list markdown."""
import pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
MANUAL = list(csv.DictReader(open(BASE / "01_数据" / "eip_manual_download.csv", encoding="utf-8-sig")))

lines = []
lines.append("# 人工下载任务清单（新项目缺失基金数据）")
lines.append("")
lines.append("> 日期：2026-08-14")
lines.append("> 用途：自动化抓取（Yahoo/FT/德系门户）到瓶颈后，剩下 91 个名称需要人工从可浏览的基金库下载。其中 71 支基金有希望、20 个（债券/结构性）免费源无解。")
lines.append("")
lines.append("## 一、三个已确认可浏览的入口")
lines.append("")
lines.append("| 入口 | 地址 | 免费深度 | 说明 |")
lines.append("|---|---|---|---|")
lines.append("| FT Markets | https://markets.ft.com/data/ | 约 1 个月日历史 | 按名称/ISIN 搜索，tearsheet 页面可直接看到净值；历史更早需登录 |")
lines.append("| fundinfo.com | https://www.fundinfo.com/en/search | 需注册（免费账号） | 专业 UCITS 基金库，按名称/ISIN/WKN/Valor 搜索 |")
lines.append("| wallstreet-online | https://www.wallstreet-online.de | 注册后可导出历史 | 德语基金门户，按 ISIN/名称可查“Historische Kurse” |")
lines.append("")
lines.append("> 注意：下载时务必核对**份额与币种**（如 ACC/DIS、USD/HKD），只取与清单一致的那一条；")
lines.append("> 保存为 `01_数据/人工下载/<基金名称>.csv`，至少含 `Date, Close`（或 NAV / Adj Close），日期格式 YYYY-MM-DD。")
lines.append("")
lines.append("## 二、71 支待下载基金")
lines.append("")
for cat in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    group = [r for r in MANUAL if r["kind"] == "基金" and r["category"].split("/")[0] == cat]
    if not group:
        continue
    lines.append(f"### {cat}（{len(group)}）")
    lines.append("")
    lines.append("| # | 基金名称 | 候选ISIN(待核) | FT历史 | FT搜索 | fundinfo | wallstreet |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(group, 1):
        ft_hist = f"[FT历史]({r['ft_hist_url']})" if r["ft_hist_url"] else "-"
        lines.append(f"| {i} | {r['name']} | {r['cand_isin'] or '-'} | {ft_hist} | [FT]({r['ft_search_url']}) | [fundinfo]({r['fundinfo_url']}) | [wso]({r['wallstreet_url']}) |")
    lines.append("")

lines.append("## 三、免费源无解（20 个，直接标记，不下载）")
lines.append("")
lines.append("| 类型 | 数量 | 说明 |")
lines.append("|---|---|---|")
lines.append("| 结构性产品/Autocall | 17 | BBVA/UBS/IDAD/MARIANA 等，无公开日频净值 |")
lines.append("| 债券/票据/国库券 | 3 | 单券历史免费源不提供 |")
lines.append("")
lines.append("## 四、误配待换（21 个）")
lines.append("")
lines.append("这 21 个目前有 Yahoo 数据但**匹配到错误基金**（见 `01_数据/eip_wrong.csv`），")
lines.append("需按第二节方式人工查到正确份额后替换，否则从建模集中剔除。")
lines.append("")
lines.append("## 五、完整机器可读清单")
lines.append("")
lines.append("- `01_数据/eip_manual_download.csv`：91 行，含全部链接。")
lines.append("- `01_数据/eip_master_status.csv`：453 个名称的最终状态账。")

out = BASE / "03_文档" / "规划" / "2026-08-14_人工下载任务清单.md"
out.write_text("\n".join(lines), encoding="utf-8")
print("written:", out)