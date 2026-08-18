"""Build boss-facing v4 robustness report as a professional Word document (v5 structure)."""

from __future__ import annotations

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

BLACK = RGBColor(0x00, 0x00, 0x00)
GRAY_DARK = RGBColor(0x33, 0x33, 0x33)
HEI = "SimHei"
YAHEI = "Microsoft YaHei"


def set_run_font(run, font_name, ea_font_name, size=None, bold=False, color=BLACK):
    run.font.name = font_name
    run.font.size = Pt(size) if size else run.font.size
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), ea_font_name)


def make_heading(doc, text, level):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        set_run_font(run, HEI, HEI, size={1: 16, 2: 14, 3: 12}.get(level, 11), bold=True, color=BLACK)
    return p


def add_normal(doc, text, size=10):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run_font(r, YAHEI, YAHEI, size=size, color=BLACK)
    return p


def shade_cell(cell, hex_color):
    tc = cell._element.get_or_add_tcPr()
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}" w:val="clear"/>')
    tc.append(shading)


def add_table(doc, headers, rows, col_widths, font_size=8):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, w in enumerate(col_widths):
        for row in table.rows:
            row.cells[i].width = w
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        shade_cell(cell, "FFFFFF")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(header)
        set_run_font(r, HEI, HEI, size=font_size + 1, bold=True, color=BLACK)
    for row_idx, row_data in enumerate(rows):
        row = table.add_row()
        for col_idx, value in enumerate(row_data):
            cell = row.cells[col_idx]
            bg = "E6E6E6" if row_idx % 2 == 1 else "FFFFFF"
            shade_cell(cell, bg)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            r = p.add_run(str(value))
            set_run_font(r, YAHEI, YAHEI, size=font_size, color=GRAY_DARK)
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>'
        '</w:tblBorders>'
    )
    table._tbl.tblPr.append(borders)
    return table


def dist_table_rows(data):
    rows = []
    for metric, full, test in data:
        rows.append([metric, "全历史"] + full)
        rows.append([metric, "2025后"] + test)
    return rows


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.17)
    sec.right_margin = Cm(3.17)

    normal = doc.styles["Normal"]
    normal.font.name = YAHEI
    normal.font.size = Pt(10)
    normal.font.color.rgb = BLACK
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), YAHEI)

    make_heading(doc, "ProFunds 策略稳健性与改善评估报告", 1)
    add_normal(doc, "日期：2026-08-18")
    add_normal(doc, "口径：m30_v2 正式版，103 支非货币基金、231 条策略；mapping 与 Excel、全部分析使用同一份当前 8/4 数据，mapping 与重算差异为 0。条件表述与正式 Excel 说明一致。")

    # 一、样本外有效性概览
    make_heading(doc, "一、样本外有效性概览", 2)
    add_normal(doc, "固定切分将历史数据分为建模段（train）与回测段（test）。严格重选指只用建模段数据重新选择策略，再用未参与建模的 2025 年后数据回测，避免选策略时看过回测成绩。")

    make_heading(doc, "1.1 现役 m30_v2 固定切分", 3)
    add_table(doc, ["指标", "口径", "min", "P10", "中位数", "P90", "max"], [
        ["命中率", "建模段", "48.00%", "54.01%", "57.28%", "60.64%", "67.13%"],
        ["命中率", "回测段", "55.06%", "57.20%", "61.59%", "66.53%", "75.51%"],
        ["平均回报", "建模段", "0.139%", "0.221%", "0.321%", "0.424%", "0.566%"],
        ["平均回报", "回测段", "0.213%", "0.323%", "0.478%", "0.773%", "1.177%"],
        ["std", "建模段", "1.21%", "1.59%", "2.27%", "3.31%", "5.21%"],
        ["std", "回测段", "0.84%", "1.47%", "2.17%", "3.08%", "3.83%"],
        ["交易数", "建模段", "51", "121", "577", "1391", "2251"],
        ["交易数", "回测段", "33", "38", "95", "175", "235"],
    ], [Cm(2.4), Cm(1.9), Cm(1.8), Cm(1.8), Cm(2.0), Cm(1.8), Cm(1.8)])
    add_normal(doc, "结论：103/103 支基金回测段命中率 >=55%，平均回报与命中率均高于建模段，未见样本外衰减。")

    make_heading(doc, "1.2 严格重选", 3)
    add_table(doc, ["指标", "口径", "min", "P10", "中位数", "P90", "max"], [
        ["命中率", "建模段", "48.00%", "54.71%", "57.20%", "61.85%", "67.13%"],
        ["命中率", "回测段", "44.00%", "55.16%", "60.47%", "65.97%", "75.61%"],
        ["平均回报", "建模段", "0.185%", "0.220%", "0.336%", "0.431%", "2.128%"],
        ["平均回报", "回测段", "-0.207%", "0.240%", "0.402%", "0.653%", "1.031%"],
        ["std", "建模段", "1.17%", "1.46%", "2.26%", "3.61%", "10.00%"],
        ["std", "回测段", "0.75%", "1.24%", "2.04%", "3.20%", "4.68%"],
        ["交易数", "建模段", "27", "103", "577", "1352", "2419"],
        ["交易数", "回测段", "30", "36", "76", "151", "206"],
    ], [Cm(2.4), Cm(1.9), Cm(1.8), Cm(1.8), Cm(2.0), Cm(1.8), Cm(1.8)])
    add_normal(doc, "结论：严格重选后仍有 99/103 支命中率 >=50%、93/103 支 >=55%，策略效果不是只靠看过回测段才成立。")

    make_heading(doc, "1.3 训练效果异常与改进", 3)
    add_normal(doc, "需要从候选池补强或替换（同时展示全历史与 2025 后）：")
    add_table(doc, ["基金", "条件", "全历史平均", "全历史命中", "2025后平均", "2025后命中", "问题"], [
        ["UDPSX", "QQQ<=-1% 且 VIX5d>0，买基金第二天", "0.205%", "57.3%", "0.536%", "67.9%", "训练效果弱且波动高"],
        ["UIPSX", "FXY<0 且 GLD>0 且 XLC>0，买基金后2日平均回报", "0.235%", "55.6%", "0.526%", "60.5%", "训练效果偏弱"],
        ["UKPIX", "XLC<0 且 信用利差>0，买基金后2日平均回报", "0.303%", "55.2%", "0.286%", "61.5%", "训练效果偏弱"],
        ["UTPSX", "GLD>0 且 JNK<0 且 XLU<0，买基金第二天", "0.236%", "55.9%", "0.396%", "59.6%", "训练效果偏弱"],
    ], [Cm(1.8), Cm(4.6), Cm(1.8), Cm(1.8), Cm(1.8), Cm(1.8), Cm(2.2)], font_size=8)
    add_normal(doc, "全历史偏弱但 2025 后明显改善，暂不删除、继续观察：")
    add_table(doc, ["基金", "条件", "全历史平均", "全历史命中", "2025后平均", "2025后命中"], [
        ["CYPSX", "EEM<0 且 SLV>0 且 XLF<0，买基金第二天", "0.218%", "59.1%", "0.483%", "65.9%"],
        ["IDPSX", "SPY<0 且 美元/黄金<=-1.0%，买基金第二天", "0.248%", "58.8%", "0.606%", "62.8%"],
        ["OEPIX", "XLU<=-1% 且 VIX收盘>0，买基金后3日平均回报", "0.317%", "55.0%", "0.610%", "65.4%"],
        ["SGPIX", "GDX>0 且 XLC<0 且 XLK<0，买基金第二天", "0.211%", "55.2%", "0.605%", "66.7%"],
        ["SVPIX", "SLV>0 且 SPY<0 且 TIP>0，买基金第二天", "0.205%", "55.7%", "0.596%", "67.5%"],
        ["UKPIX", "LQD<0 且 TIP<0 且 XLC<0，买基金后2日平均回报", "0.247%", "57.5%", "0.405%", "64.3%"],
    ], [Cm(1.8), Cm(4.6), Cm(1.8), Cm(1.8), Cm(1.8), Cm(1.8)], font_size=8)
    add_normal(doc, "改进措施：优先用候选池中更显著的信号替换 4 条训练弱策略；全历史弱但 2025 后强的 6 条继续观察，不为了凑覆盖硬塞低质量信号。")

    # 二、策略解释概览
    make_heading(doc, "二、策略解释概览", 2)
    add_normal(doc, "231 条策略已逐条给出经济解释，输出列包括“触发条件”“条件解释”与“机制”，不含条件代码和历史统计；全部明细见 v4_strategy_explanation_v3.csv。")

    make_heading(doc, "2.1 反向基金方向冲突（需改善）", 3)
    add_normal(doc, "反向基金应在标的下跌时上涨，但以下策略在“标的上涨/风险偏好回暖”条件下买入反向基金，等于赌风险偏好次日立即反转，经济逻辑弱：")
    add_table(doc, ["基金", "条件", "平均回报", "命中率", "问题"], [
        ["BITIX", "EEM>0 且 JNK>0 且 SPY>0，买基金第二天", "0.312%", "55.9%", "反向基金使用风险偏好条件"],
        ["BITIX", "EEM>0 且 GLD>0 且 SLV>0，买基金后2日平均回报", "0.346%", "55.0%", "反向基金使用风险偏好+贵金属条件"],
        ["SNPIX", "QQQ>0 且 XLC>0 且 XLV>0，买基金第二天", "0.371%", "57.0%", "反向基金使用风险偏好条件"],
        ["SNPSX", "SPY>0 且 XLC>0 且 XLK>0，买基金第二天", "0.421%", "61.5%", "反向基金使用风险偏好条件"],
        ["UCPIX", "JNK>0 且 LQD<0 且 XLC>0，买基金第二天", "0.319%", "55.3%", "反向基金信用信号混乱"],
        ["UHPIX", "HYG>0 且 SLV>0 且 XLC>0，买基金第二天", "0.428%", "57.3%", "反向基金使用风险偏好+贵金属条件"],
        ["UHPSX", "FXY<0 且 IWM>0 且 XLE<0，买基金第二天", "0.564%", "57.9%", "反向基金条件方向不明"],
        ["UKPSX", "QQQ>0 且 SPY>0 且 TIP<0，买基金第二天", "0.390%", "58.6%", "反向基金使用风险偏好条件"],
        ["USPIX", "EEM>0 且 SLV>0 且 XLV>0，买基金第二天", "0.497%", "56.6%", "反向基金使用风险偏好条件"],
        ["USPSX", "EEM>0 且 GLD>0 且 HYG>0，买基金第二天", "0.487%", "55.4%", "反向基金使用风险偏好+避险条件"],
        ["UVPIX", "EEM>0 且 UUP>0 且 XLF<0，买基金第二天", "0.300%", "58.3%", "反向基金使用新兴市场上涨条件"],
    ], [Cm(1.7), Cm(4.6), Cm(1.7), Cm(1.7), Cm(3.3)], font_size=8)

    make_heading(doc, "2.2 比特币基金解释受限（情有可原）", 3)
    add_table(doc, ["基金", "条件", "平均回报", "命中率", "原因"], [
        ["BITIX", "XLC>0 且 该基金当日回报<0，买基金第二天", "0.565%", "57.9%", "无比特币参考ETF，只能依赖代理变量"],
        ["BTCFX", "QQQ<0 且 XLK<0 且 XLV<0，买基金第二天", "0.687%", "57.1%", "无比特币参考ETF，只能依赖代理变量"],
        ["BTCFX", "EEM<0 且 信用利差<0，买基金后2日平均回报", "0.414%", "56.4%", "无比特币参考ETF，只能依赖代理变量"],
        ["BTCFX", "EEM<0 且 IWM<0 且 SPY<0，买基金后2日平均回报", "0.461%", "56.6%", "无比特币参考ETF，只能依赖代理变量"],
    ], [Cm(1.7), Cm(4.6), Cm(1.7), Cm(1.7), Cm(3.3)], font_size=8)
    add_normal(doc, "改进措施：反向基金优先替换为方向一致的条件，例如做空新兴市场用 EEM<0、做空科技用 QQQ<0 或 XLK<0；若保留，须明确标注为均值回归逻辑并做样本外验证。比特币基金暂不处理，未来加入加密参考资产后优先重做。")

    # 三、风险概览
    make_heading(doc, "三、风险概览", 2)

    make_heading(doc, "3.1 合并策略风险分布与波动比值（103 基金）", 3)
    add_normal(doc, "合并策略相对基金无条件波动比值：min 0.491，P10 0.686，中位数 1.023，P90 1.277，max 1.535。")
    add_table(doc, ["比值区间", "基金数", "占比"], [
        ["<0.5x", "1", "0.97%"],
        ["0.5-1.0x", "46", "44.66%"],
        ["1.0-1.5x", "54", "52.43%"],
        ["1.5-2.0x", "2", "1.94%"],
        [">2.0x", "0", "0.00%"],
    ], [Cm(4.0), Cm(3.5), Cm(3.5)])
    add_normal(doc, "详细指标分布：")
    merged_rows = dist_table_rows([
        ("平均回报", ["0.207%", "0.247%", "0.361%", "0.445%", "0.523%"], ["0.213%", "0.323%", "0.478%", "0.773%", "1.177%"]),
        ("命中率", ["53.79%", "55.38%", "57.93%", "61.07%", "66.32%"], ["55.06%", "57.20%", "61.59%", "66.53%", "75.51%"]),
        ("std", ["1.25%", "1.57%", "2.27%", "3.22%", "4.46%"], ["0.84%", "1.47%", "2.17%", "3.08%", "3.83%"]),
        ("年化波动", ["19.78%", "24.90%", "36.09%", "51.11%", "70.85%"], ["13.35%", "23.31%", "34.42%", "48.91%", "60.72%"]),
        ("下行标准差", ["0.71%", "0.85%", "1.36%", "2.00%", "2.98%"], ["0.40%", "0.55%", "1.03%", "1.68%", "2.21%"]),
        ("平均/std", ["0.076", "0.107", "0.156", "0.224", "0.270"], ["0.109", "0.163", "0.248", "0.355", "0.406"]),
        ("t 统计量", ["1.05", "2.41", "3.92", "5.63", "6.51"], ["0.65", "1.57", "2.31", "3.11", "4.18"]),
    ])
    add_table(doc, ["指标", "口径", "min", "P10", "中位数", "P90", "max"], merged_rows,
              [Cm(2.4), Cm(1.9), Cm(1.8), Cm(1.8), Cm(2.0), Cm(1.8), Cm(1.8)], font_size=8)

    make_heading(doc, "3.2 单策略风险分布（231 条）", 3)
    add_normal(doc, "单策略相对基金无条件波动比值：min 0.442，P10 0.635，中位数 1.026，P90 1.328，max 1.655。")
    add_table(doc, ["比值区间", "策略数", "占比"], [
        ["<0.5x", "4", "1.73%"],
        ["0.5-1.0x", "107", "46.32%"],
        ["1.0-1.5x", "111", "48.05%"],
        ["1.5-2.0x", "9", "3.90%"],
        [">2.0x", "0", "0.00%"],
    ], [Cm(4.0), Cm(3.5), Cm(3.5)])
    add_normal(doc, "详细指标分布：")
    single_rows = dist_table_rows([
        ("平均回报", ["0.202%", "0.255%", "0.358%", "0.520%", "0.952%"], ["0.204%", "0.286%", "0.555%", "0.938%", "1.827%"]),
        ("命中率", ["54.97%", "55.43%", "58.00%", "62.20%", "66.32%"], ["53.97%", "56.41%", "62.22%", "68.33%", "80.49%"]),
        ("std", ["0.82%", "1.56%", "2.21%", "3.73%", "5.04%"], ["0.79%", "1.32%", "2.19%", "3.53%", "5.11%"]),
        ("年化波动", ["13.03%", "24.79%", "35.13%", "59.14%", "79.93%"], ["12.56%", "20.88%", "34.84%", "56.12%", "81.13%"]),
        ("下行标准差", ["0.41%", "0.85%", "1.36%", "2.30%", "3.50%"], ["0.21%", "0.60%", "1.06%", "2.06%", "3.08%"]),
        ("平均/std", ["0.057", "0.104", "0.161", "0.225", "0.359"], ["0.091", "0.142", "0.270", "0.391", "0.748"]),
        ("t 统计量", ["1.05", "2.13", "3.22", "4.17", "5.16"], ["0.59", "1.07", "1.93", "2.84", "4.93"]),
    ])
    add_table(doc, ["指标", "口径", "min", "P10", "中位数", "P90", "max"], single_rows,
              [Cm(2.4), Cm(1.9), Cm(1.8), Cm(1.8), Cm(2.0), Cm(1.8), Cm(1.8)], font_size=8)

    make_heading(doc, "3.3 风险异常与改进", 3)
    add_normal(doc, "需观察基金（合并层面，含比值 >=1.5）：")
    add_table(doc, ["基金", "关注点", "数值", "说明"], [
        ["BLPIX", "合并 std 为基金无条件 std 的 1.54 倍", "1.80% vs 1.17%", "杠杆多头，波动高于基金本身"],
        ["BLPSX", "合并 std 为基金无条件 std 的 1.52 倍", "1.79% vs 1.18%", "杠杆多头，波动高于基金本身"],
        ["SPPIX", "2025 后 std 高于建模段 1.5 倍", "3.05% vs 2.02%", "反向贵金属，波动上升需观察"],
        ["SPPSX", "2025 后 std 高于建模段 1.5 倍", "3.05% vs 2.02%", "反向贵金属，波动上升需观察"],
        ["UXPSX", "2025 后 std 高于建模段 1.5 倍", "1.95% vs 1.21%", "反向国际，波动上升需观察"],
    ], [Cm(1.8), Cm(4.5), Cm(2.8), Cm(3.8)], font_size=8)
    add_normal(doc, "情有可原（杠杆/反向产品，波动高是基金本身特质，不是策略选错）：")
    add_table(doc, ["基金", "关注点", "备注"], [
        ["PMPIX / PMPSX", "策略 std 4.64% / 4.63%", "基金本身全历史 std 3.53% / 3.59%，最大单笔亏损 -24.9%；贵金属 UltraSector 杠杆产品"],
        ["UHPIX", "策略 std 4.46%", "基金本身全历史 std 4.17%，最大单笔亏损 -50.0%；Ultra Short China 反向杠杆"],
        ["UBPIX / UBPSX", "最大单笔亏损 -40.5%", "基金本身全历史 std 4.02%，最大单笔亏损 -40.5%；Ultra Latin America 杠杆"],
        ["UAPIX / UAPSX", "最大单笔亏损 -32.4%", "基金本身全历史 std 3.13% / 3.02%，最大单笔亏损 -50.0% / -41.5%；Ultra Small-Cap 杠杆"],
        ["UGPSX", "2025 后 std 5.11%", "基金本身全历史 std 4.21%，最大单笔亏损 -26.0%；Ultra China 杠杆"],
        ["SMPIX / SMPSX / UGPIX", "2025 后 std 4.48%-4.90%", "基金本身全历史 std 3.13% / 3.14% / 4.23%；UltraSector/Ultra 杠杆"],
    ], [Cm(3.0), Cm(4.0), Cm(7.0)], font_size=8)
    add_normal(doc, "改进措施：SPPIX/SPPSX/UXPSX 列入观察名单，若波动继续上升再评估增加风险门槛；BLPIX/BLPSX 因合并比值 >=1.5 保留在需观察；其余杠杆/反向产品波动高是基金本身特质，不删除。")

    # 四、阈值单调性概览
    make_heading(doc, "四、阈值单调性概览", 2)
    add_normal(doc, "本章假设：对单个策略，把某个条件阈值改深，例如 XLK<=-1% 且 该基金当日回报<=-2% 中的 XLK 改为 <=-2%/-2.5%/-3%，整个策略的平均回报和命中率应递增。以下全部按策略统计；多条件策略只调整被扫描的那个条件，其他子条件保持不变。")

    make_heading(doc, "4.1 策略阈值扫描汇总", 3)
    add_normal(doc, "负向阈值扫描（策略级，其余条件固定）：")
    add_table(doc, ["阈值", "平均回报中位数", "命中率中位数", "交易数中位数"], [
        ["-0.5%", "0.245%", "55.2%", "1041"],
        ["-1%", "0.308%", "56.5%", "606"],
        ["-1.5%", "0.327%", "56.6%", "370"],
        ["-2%", "0.482%", "57.7%", "217"],
        ["-2.5%", "0.290%", "56.5%", "155"],
        ["-3%", "0.266%", "56.2%", "240"],
    ], [Cm(3.0), Cm(3.6), Cm(3.0), Cm(3.0)], font_size=8)
    add_normal(doc, "正向阈值扫描（策略级，其余条件固定）：")
    add_table(doc, ["阈值", "平均回报中位数", "命中率中位数", "交易数中位数"], [
        ["+0.5%", "0.188%", "56.6%", "560"],
        ["+1%", "0.300%", "59.2%", "257"],
        ["+1.5%", "0.419%", "59.6%", "86"],
        ["+2%", "0.468%", "63.0%", "19"],
        ["+2.5%", "0.387%", "75.0%", "14"],
        ["+3%", "0.389%", "52.0%", "25"],
    ], [Cm(3.0), Cm(3.6), Cm(3.0), Cm(3.0)], font_size=8)
    add_normal(doc, "结论：负向和正向都在 -2%/+2% 附近达到平均回报中位数峰值，更深阈值不再单调上升；+2.5%/+3% 策略数很少，中位数参考意义有限。")

    make_heading(doc, "4.2 策略连跌扫描（策略级）", 3)
    add_normal(doc, "现役策略中只有 GVPSX 使用 self_3down（长期国债下跌 且 该基金连续3日下跌），按策略扫描连续下跌天数，其他条件固定：")
    add_table(doc, ["连续下跌天数", "平均回报", "命中率", "交易数"], [
        ["1 天", "-0.029%", "50.2%", "793"],
        ["2 天", "+0.097%", "54.3%", "1023"],
        ["3 天", "+0.207%", "58.0%", "400"],
        ["4 天", "+0.278%", "59.6%", "89"],
        ["5 天", "无触发", "无", "0"],
    ], [Cm(3.0), Cm(3.6), Cm(3.0), Cm(3.0)], font_size=8)
    add_normal(doc, "结论：连跌天数从 1 增至 4，平均回报与命中率单调上升，符合“连跌越久反弹越强”的假设；第 5 天叠加外部条件后无触发。")

    make_heading(doc, "4.3 方向相反的策略（逐策略展开）", 3)
    add_normal(doc, "以下 5 条策略的阈值加深方向与全策略中位数明显相反（相关系数 < -0.5），逐策略展示平均回报、命中率、交易数。多条件策略只调整被扫描条件，其余条件固定。")

    add_normal(doc, "CYPIX：XLK<=-1% 且 该基金当日回报<=-2%，买基金第二天（只调整 XLK 阈值，自身大跌固定 -2%）")
    add_table(doc, ["阈值", "平均回报", "命中率", "交易数"], [
        ["-0.5%", "0.326%", "54.0%", "202"],
        ["-1%", "0.482%", "56.7%", "217"],
        ["-1.5%", "0.455%", "60.0%", "145"],
        ["-2%", "0.641%", "61.9%", "118"],
        ["-2.5%", "0.217%", "55.4%", "65"],
        ["-3%", "-0.388%", "52.9%", "17"],
    ], [Cm(2.5), Cm(3.0), Cm(3.0), Cm(3.0)], font_size=8)

    add_normal(doc, "UBPIX：QQQ<=-1% 且 VIX>0，买基金第二天（只调整 QQQ 阈值，VIX>0 固定）")
    add_table(doc, ["阈值", "平均回报", "命中率", "交易数"], [
        ["-0.5%", "0.258%", "54.8%", "882"],
        ["-1%", "0.437%", "56.8%", "588"],
        ["-1.5%", "0.378%", "57.6%", "370"],
        ["-2%", "0.285%", "57.4%", "195"],
        ["-2.5%", "-0.422%", "54.2%", "83"],
        ["-3%", "-1.864%", "0.0%", "1"],
    ], [Cm(2.5), Cm(3.0), Cm(3.0), Cm(3.0)], font_size=8)

    add_normal(doc, "UBPSX：QQQ<=-1% 且 VIX>0，买基金第二天（只调整 QQQ 阈值，VIX>0 固定）")
    add_table(doc, ["阈值", "平均回报", "命中率", "交易数"], [
        ["-0.5%", "0.253%", "55.2%", "892"],
        ["-1%", "0.432%", "56.5%", "588"],
        ["-1.5%", "0.367%", "57.0%", "370"],
        ["-2%", "0.274%", "56.9%", "195"],
        ["-2.5%", "-0.430%", "54.2%", "83"],
        ["-3%", "-1.843%", "0.0%", "1"],
    ], [Cm(2.5), Cm(3.0), Cm(3.0), Cm(3.0)], font_size=8)

    add_normal(doc, "UDPSX：QQQ<=-1% 且 VIX5d>0，买基金第二天（只调整 QQQ 阈值，VIX5d>0 固定）")
    add_table(doc, ["阈值", "平均回报", "命中率", "交易数"], [
        ["-0.5%", "0.192%", "56.0%", "839"],
        ["-1%", "0.205%", "57.3%", "517"],
        ["-1.5%", "0.182%", "56.8%", "317"],
        ["-2%", "-0.057%", "53.3%", "165"],
        ["-2.5%", "-0.274%", "52.9%", "68"],
        ["-3%", "无触发", "无", "0"],
    ], [Cm(2.5), Cm(3.0), Cm(3.0), Cm(3.0)], font_size=8)

    add_normal(doc, "ULPIX：QQQ<=-1% 且 VIX5d>0，买基金第二天（只调整 QQQ 阈值，VIX5d>0 固定）")
    add_table(doc, ["阈值", "平均回报", "命中率", "交易数"], [
        ["-0.5%", "0.238%", "54.9%", "839"],
        ["-1%", "0.255%", "55.9%", "517"],
        ["-1.5%", "0.270%", "56.2%", "317"],
        ["-2%", "0.071%", "53.3%", "165"],
        ["-2.5%", "-0.021%", "53.6%", "69"],
        ["-3%", "无触发", "无", "0"],
    ], [Cm(2.5), Cm(3.0), Cm(3.0), Cm(3.0)], font_size=8)

    add_normal(doc, "改进措施：这 5 条策略不做“更深阈值”外推，当前 -1% 阈值反而更优；其余策略保持 -2% 固定阈值即可。")

    out = r"C:\Users\vanessacen\Desktop\新基金预测\03_文档\报告\2026-08-18_v4稳健性分析报告_上司版.docx"
    doc.save(out)
    print("OK: " + out)


if __name__ == "__main__":
    main()
