# -*- coding: utf-8 -*-
"""investing.com 覆盖判断 + 手动下载搜索词清单（新项目缺失基金）。
输入：01_数据/eip_manual_download.csv
输出：01_数据/eip_investing_coverage.csv、03_文档/规划/2026-08-14_investing搜索词清单_手动下载.md
"""
import pathlib, csv, urllib.parse

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")

# status: 有=基金家族/所需份额确认在 investing；需核=家族在但份额未确认；无=整体未找到；不适用=结构化/ETP
COV = {
"ABERDEEN STD - NORTH AMERICAN SMALLER COMPANIES FUND I ACC USD USD": dict(status="有", term="abrdn American Growth - Smaller Companies", url="https://au.investing.com/funds/aberdeen-american-growthsmaller-company-profile", note="页面标题即 Aberdeen Standard SICAV I - North American Smaller Companies；下载时核对 I ACC USD 份额"),
"ALLIANCE BERNSTEIN AMERICAN INCOME PORTFOLIO INC USD": dict(status="有", term="American Income Portfolio", url="https://www.investing.com/funds/american-income-portfolio-a2-ace-company-profile", note="A2 Acc=0P000019TN；INC 份额选 A Income（持仓页可见 A Ine），核对份额/币种"),
"ALLIANCEBERNSTEIN AMERICAN INCOME USD": dict(status="有", term="American Income Portfolio S USD Acc", url="https://au.investing.com/funds/american-income-portfolio-s-usd-acc-scoreboard", note="S USD Acc=0P00011R8T，ISIN LU0231611335；与上一条同家族不同份额"),
"AMUNDI BD GLOBAL AGG AUC 3D USD": dict(status="有", term="Amundi Funds Global Aggregate Bond", url="https://se.investing.com/funds/amundi-global-aggreg-bond-a-usd-c-company-profile", note="A USD (C)=0P0000A48C；清单里 'AUC 3D' 疑似其缩写，下载时核对份额"),
"ARBROOK G10 AMERICAN EQUITIES A1 USD ACC USD": dict(status="无", term="", url="", note="多轮搜索未找到（Arbrook 为小众管理人）"),
"ARTISAN PTNRS GBL GLOBAL OPPORTUNITIES I USD": dict(status="有", term="Artisan Global Opportunities", url="https://ca.investing.com/funds/artisan-global-opportunities-inv-company-profile", note="US 份额 ARTRX/APHRX、I EUR=0P0000X7XK 已确认；选 I USD 下载"),
"BLACKROCK (LUX) SA BGF GLOBAL INFL L A2 USD": dict(status="有", term="BlackRock Global Inflation Linked Bond", url="https://www.investing.com/funds/global-inflation-linked-bond-fund-x-company-profile", note="家族已确认（E2/X2 等）；选 A2 USD 份额下载"),
"BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPP A2 USD USD": dict(status="有", term="BlackRock Fixed Income Global Opportunities", url="https://fi.investing.com/funds/blackrock-fixed-income-globl-opp-a2-company-profile", note="A2=0P00008FSR；确认 USD 份额"),
"BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPPS D5 USD": dict(status="需核", term="BlackRock Fixed Income Global Opportunities D5", url="", note="家族已确认（A2/C2）；D5 USD 份额需在 investing 内核对"),
"CAPITAL CITIGROUP GLOBAL MARKETS FUNDING MEMORY COUPON USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BBVA GLOBAL QUAD INCOME USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 3 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 4 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 7 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 8 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 9 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CAUSEWAY MORGAN STANLEY GLOBAL MARKETS INCOME NOTE USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CELERITY GLOBAL BALANCED FUND IC A ACC USD": dict(status="无", term="", url="", note="未找到（只有 Celerius，非同一基金）"),
"COMMERZBANK GLOBAL INDEX INCOME BUILDER 70-70 NOV 18 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"CT MGMT AMERICAN 3U USD ACC USD": dict(status="无", term="", url="", note="ISIN LU1864949380 investing 未收录；investing 只有 CT (Lux) American Smaller Companies 系列"),
"CTMGMT LUX AMERICAN AU USD ACC USD": dict(status="需核", term="CT (Lux) American", url="https://se.investing.com/funds/lu1878469607-company-profile", note="家族已确认（American Smaller Companies 系列）；'American AU' 份额需核对"),
"FINCREST GLOBAL EQUITY FUND CLASS A USD": dict(status="无", term="", url="", note="未找到"),
"FRANKLIN TEMP GLOBAL HI YLD MDIS \\$ USD": dict(status="有", term="Franklin High Yield Fund", url="https://uk.investing.com/funds/lu0889566138-user-rankings", note="家族已确认（N(Mdis)USD=0P0000Y5Q7）；选 A(Mdis)USD 份额下载"),
"FRANKLIN TEMP GLOBAL INC A ACC USD USD": dict(status="有", term="Templeton Global Income Fund", url="https://hk.investing.com/funds/lu0976567544-company-profile", note="家族已确认（A(Mdis)SGD-H1=0P0000ZT9O）；选 A(acc)USD 份额下载"),
"FRANKLIN TEMPL GLOBAL FOCUS FD A DIS USD": dict(status="无", term="", url="", note="Franklin Global Focus 未找到"),
"FRANKLIN TEMPLETON FRANKLIN MUT GLOBAL DVRY A CAP USD": dict(status="有", term="Franklin Mutual Global Discovery", url="https://cn.investing.com/funds/franklin-mutual-global-discovery-a-company-profile", note="US 份额 TEDIX/FMDRX 已确认；离岸 A(acc)USD 需核对"),
"FRANKLIN TEMPLETON GLOBAL FOCUS A ACC USD": dict(status="无", term="", url="", note="Franklin Global Focus 未找到"),
"FRANKLIN TEMPLETON GLOBAL TOTAL RETURN A MDIS USD USD": dict(status="有", term="Templeton Global Total Return", url="https://hk.investing.com/funds/t-global-total-return-fund-a-acc-us#1", note="A(acc)USD=0P00000HPA 已确认；选 A(Mdis)USD 份额下载"),
"FRANKLIN TEMPLETON GLOBAL TOTAL RETURN FUN A ACC USD USD": dict(status="有", term="Templeton Global Total Return", url="https://hk.investing.com/funds/t-global-total-return-fund-a-acc-us#1", note="A(acc)USD=0P00000HPA，正好匹配"),
"FRANKLIN TEMPLETON LATIN AMERICA A ACC USD": dict(status="有", term="Templeton Latin America", url="https://hk.investing.com/funds/templeton-latin-americafund-aaccusd#1", note="A(acc)USD=0P00000B0V，正好匹配"),
"FTGF GBL BRANDYWNE GLOBAL FIXED INCOME A USD ACC USD": dict(status="有", term="FTGF Brandywine Global Fixed Income", url="https://pt.investing.com/funds/fixed-income-fund-class-lm-ususd-ac-company-profile", note="LM Class US$ Acc=0P0000Z6UY、Premier=0P0000RWW1 已确认；选 A Class US$ Acc 下载"),
"FTGF GBL W/A GLOBAL HIGH YIELD A USD ACC USD": dict(status="无", term="", url="", note="Western Asset Global High Yield UCITS 未找到（investing 只有美国封闭式 EHI 与 FTGF 美国高收益）"),
"GLOBAL X FDS GBL X FTSE ARGENT USD USD": dict(status="有", term="Global X FTSE Argentina 20", url="https://cn.investing.com/etfs/global-x-ftse-argentina-20-historical-data?cid=1214670", note="ARGT（美国 ETF）历史数据页可直接导出；确认币种/上市地"),
"GLOBAL X FDS GBL X ROBOTICS & ARTIFICIAL USD": dict(status="有", term="Global X Robotics & Artificial Intelligence", url="https://hk.investing.com/etfs/global-x-robotics---ai-usd#1", note="BOTZ（美国）/ XB0T（UCITS，ISIN IE00BLCHJB90）；历史数据页可导出"),
"GUINNESS GAM GLOBAL EQUITY INCOME INC D USD": dict(status="有", term="Guinness Global Equity Income", url="https://ph.investing.com/funds/guinness-global-equity-income-z-holdings", note="Z/D/Y 份额已确认；选 D USD Inc 份额下载"),
"IDAD NATIXIS GLOBAL INDICES AC JULY 2026 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC APRIL 2026 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC DEC 2025 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"INVESCO MANAGEMENT GLOBAL EQUITY INCOME A USD ACC NAV USD": dict(status="有", term="Invesco Global Equity Income", url="https://ca.investing.com/funds/gb00b8n46178#1", note="UK Z Inc=0P0000XBQW、A AUD hedged 已确认；卢森堡 A USD Acc（LU0607513230）需核对"),
"INVESCO MANAGEMENT GLOBAL SMALL CAP EQUITY A USD": dict(status="有", term="Invesco Global Small Cap Equity", url="https://hk.investing.com/funds/invesco-european-small-company-a#1", note="US ESMAX 已确认；卢森堡 A USD（LU1075211273）需核对"),
"iShares Macquarie Global Infra USD": dict(status="有", term="iShares Global Infrastructure UCITS", url="https://www.investing.com/etfs/ishares-macquarie-global-inf.-100-holdings?cid=995525", note="IDIN/INFR UCITS ETF USD (Dist)；历史数据可导出"),
"JPM IF GLOBAL DIVIDEND C ACC USD": dict(status="有", term="JPMorgan Global Dividend", url="https://cn.investing.com/funds/jpmorgan-invs-glbl-div-c-acc-usd#1", note="C (acc) USD=0P0000XC5F，正好匹配"),
"JPMF A JPMF AMERICA EQUITY A USD USD": dict(status="有", term="JPMorgan America Equity", url="https://cn.investing.com/funds/jpmorgan-america-eq-fund-a-acc-usd-company-profile#1", note="A (acc) USD=0P000019D5，正好匹配"),
"JPMF AM GLOBAL EQUITY A DIST USD USD": dict(status="需核", term="JPMorgan Funds Global Equity", url="https://au.investing.com/funds/jpi-global-select-equity-fund-a-acu-company-profile#1", note="只确认到 Global Select Equity A(acc)USD=0P00000DS2（不同基金）；'Global Equity A dist USD' 需在 investing 内搜索核对"),
"JPMORGAN IF ASSET MGM GLOBAL BAL HGD A ACC USD USD": dict(status="有", term="JPMorgan Global Balanced", url="https://cn.investing.com/funds/jpi-global-balanced-fund-c-acc-usd#1", note="C (acc) USD hedged=0P000115RQ 已确认；选 A (acc) USD hedged 下载"),
"JPMORGAN IF ASSET MGM GLOBAL INCOME HEDGED A USD ACC NAV USD USD": dict(status="有", term="JPMorgan Global Income", url="https://ms.investing.com/funds/jpi-global-income-fund-a-div-usd-he-company-profile", note="A (div) USD hedged=0P0000V47Q 已确认；选 A (acc) USD hedged 下载"),
"JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS A HGD USD": dict(status="有", term="JPMorgan Global Macro Opportunities", url="https://ca.investing.com/funds/lu1181866309-scoreboard", note="A (acc) USD hedged=0P00015EF8，正好匹配"),
"JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS C USD ACC USD": dict(status="有", term="JPMorgan Global Macro Opportunities C", url="https://il.investing.com/funds/jpm-global-macro-opp-c-acc-eur-company-profile", note="C (acc) EUR=0P00000DQ4 已确认；选 C (acc) USD 下载"),
"JPMORGAN IF GLOBAL INCOME C DIS HDG USD": dict(status="有", term="JPMorgan Global Income C", url="https://hk.investing.com/funds/jpi-global-income-fund-d-mth-usd-he-holdings", note="D (mth) USD hedged=0P0000X5GN 已确认；选 C (dis/div) USD hedged 下载"),
"JSS EMERGINGSAR GLOBAL A DIST USD": dict(status="需核", term="JSS Sustainable Equity Global", url="https://cn.investing.com/funds/jss-oekosar-eq-glbl-p-eur-dist-company-profile", note="Global Thematic P/I/M EUR 已确认；'Global A USD dist' 需核对（可能叫 JSS Sustainable Equity - Global A USD dist）"),
"LEVERAGE VANILLA GLOBAL BALANCED INVESTMENT ETP USD": dict(status="不适用", term="", url="", note="ETP，investing 无此产品"),
"MARIANA BBVA GLOBAL MARKETS MEMORY INCOME GENERATOR 8560 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"MARIANA GLOBAL GROWTH KICK OUT NOTE V2 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"MARIANA INVESTEC GLOBAL INDEX INCOME BUILDER 65 USD": dict(status="不适用", term="", url="", note="结构化票据，investing 无此产品"),
"MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL EQUITY FUND A USD ACCUMULATION USD": dict(status="无", term="", url="", note="investing 无 Montlake/Quilter Cheviot 这两只基金"),
"MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL GROWTH FUND A USD ACCUMULATION USD": dict(status="无", term="", url="", note="investing 无 Montlake/Quilter Cheviot 这两只基金"),
"NATIXIS INTL (LUX) HARRIS ASSOCS GLOBAL EQUITY I ACC USD": dict(status="有", term="Harris Associates Global Equity", url="https://il.investing.com/funds/natixisluxi-harrisassoc-glbleqragbp-company-profile", note="家族已确认（R/A GBP=0P00011SQN、P/A SGD、R/A EUR）；选 I/A USD 下载"),
"NEUBERGER BERMN II GLOBAL SNR FTG RTE INC I US USD": dict(status="无", term="", url="", note="只有 NB Global Floating Rate（NBMI 封闭式，不同产品）"),
"NG MORNINGSTAR GLOBAL DEFENSIV A USD ACC USD": dict(status="无", term="", url="", note="未找到"),
"NG MORNINGSTAR GLOBAL GROWTH A USD ACC USD": dict(status="无", term="", url="", note="未找到"),
"PICTET FUNDS GLOBAL MEGATREND SEL I USD ACC USD": dict(status="有", term="Pictet Global Megatrend Selection I USD", url="https://hk.investing.com/funds/pimegatrend-selection-i-usd#1", note="I USD=0P0000I3X7，正好匹配"),
"PICTET FUNDS GLOBAL MEGATREND SELECTION P ACC USD USD": dict(status="有", term="Pictet Global Megatrend Selection P USD", url="https://cn.investing.com/funds/pictet-global-megatrend-selection-p-company-profile", note="P USD 已确认；下载时核对份额"),
"PIMCOG GLOBAL ADVIS INCOME PU INC USD": dict(status="需核", term="PIMCO GIS Income Fund", url="https://www.investing.com/funds/ie00bym81516#1", note="E/Investor/Admin USD 份额已确认；'PU'=P USD Income 需核对"),
"PROSPER FDS SICAV GLOBAL MACRO I USD": dict(status="需核", term="Prosper Funds SICAV Global Macro", url="https://cn.investing.com/funds/prosper-stars-stripes-fund-i-eur-company-profile", note="同 SICAV 的 Stars & Stripes I EUR=0P00011MOB 已确认；Global Macro I USD 需核对"),
"RUSSELL OLD MUTUAL VALUE GLOBAL EQUITY E ACC USD": dict(status="无", term="", url="", note="Russell 家族（Multi-style/World Selection）在，但 Old Mutual Value 未找到"),
"RUSSELL OPENWORLD GLOBAL HIGH DIVIDEND EQUITY I USD": dict(status="无", term="", url="", note="OpenWorld Global Listed Infrastructure=0P0000VV1E 在，但 Global High Dividend 未找到"),
"SCHRODER INV MGMT QEP GLOBAL ACTIVE VAL A ACC USD USD": dict(status="有", term="Schroder QEP Global Active Value", url="https://cn.investing.com/funds/schroder-qep-glblactive-value-i-acc-company-profile", note="I Acc USD=0P000018N8 已确认；选 A Acc USD 下载"),
"THREADNEEDLE LATIN AMERICAN NAV ACC USD": dict(status="无", term="", url="", note="investing 无 Threadneedle Latin American（UK OEIC）"),
"VONTOBEL MGMT SA MIV GLOBAL MEDTECH P3 USD R USD": dict(status="有", term="MIV Global Medtech", url="https://uk.investing.com/funds/variopartner-s-miv-global-medtech-u-company-profile", note="P3 USD Cap=0P0000ZSTV，正好匹配"),
"VULCAN GLOBAL VALU VALUE EQUITY USD II INC NAV USD": dict(status="需核", term="Vulcan Value Equity", url="https://ph.investing.com/funds/ie00bc7gwl98-company-profile", note="Vulcan Value Equity USD Inc=0P0000ZQWR 已确认；'II Inc' 份额需核对"),
}

def search_url(term):
    return f"https://www.investing.com/search/?q={urllib.parse.quote(term)}" if term else ""

rows = list(csv.DictReader(open(BASE / "01_数据" / "eip_manual_download.csv", encoding="utf-8-sig")))
funds = [r for r in rows if r["kind"] == "基金"]

missing = [r["name"] for r in funds if r["name"] not in COV]
if missing:
    raise SystemExit("未覆盖: " + " | ".join(missing))

# 1) 覆盖表 CSV（91 行全保留）
out_rows = []
for r in rows:
    if r["kind"] == "基金":
        c = COV[r["name"]]
        out_rows.append({**r,
                         "investing_status": c["status"],
                         "investing_search": c["term"],
                         "investing_search_url": search_url(c["term"]),
                         "investing_url": c["url"],
                         "investing_note": c["note"]})
    else:
        out_rows.append({**r,
                         "investing_status": "不适用-非基金",
                         "investing_search": "",
                         "investing_search_url": "",
                         "investing_url": "",
                         "investing_note": "债券/结构性，investing 无此产品"})

fieldnames = list(out_rows[0].keys())
with open(BASE / "01_数据" / "eip_investing_coverage.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader(); w.writerows(out_rows)

# 2) 搜索词清单 md
lines = []
lines.append("# investing.com 覆盖判断与手动下载搜索词清单")
lines.append("")
lines.append("> 日期：2026-08-17")
lines.append("> 方法：对 71 支待下载基金逐支做 `site:investing.com` 网页搜索判断覆盖，再给出 investing.com 站内搜索词供手动下载。")
lines.append("> 说明：只能判断『基金家族在不在 investing』，具体份额（ACC/DIS、USD/HKD）需进页核对。")
lines.append("")
lines.append("## 一、怎么用")
lines.append("")
lines.append("1. 打开 https://www.investing.com/ ，把『搜索词』粘进顶部搜索框，回车。")
lines.append("2. 在结果里选**与清单份额/币种一致**的那一条（如 A/USD/ACC），点进基金页。")
lines.append("3. 点 **Historical Data**（历史数据），把时间范围按年拉满，页面可导出 CSV（格式同你已下载的 `US Cotton #2 Futures Historical Data.csv`：`Date,Price,Open,High,Low,Vol.,Change %`）。")
lines.append("4. 保存为 `01_数据/人工下载/<基金名称>.csv`（文件名用清单里的名字即可），至少保留 `Date, Close`。")
lines.append("")
lines.append("> ⚠️ 份额/币种务必核对：同名基金有 ACC/DIS、USD/HKD/EUR 等多个份额，只取清单要求的那一条；")
lines.append("> 拿不准就标记『份额待核』，不要拿不同份额冒充。")
lines.append("")
lines.append("## 二、覆盖统计（71 支）")
lines.append("")
lines.append("| 状态 | 数量 | 说明 |")
lines.append("|---|---|---|")
lines.append(f"| 有 | {sum(1 for r in funds if COV[r['name']]['status']=='有')} | 基金家族已在 investing 确认，按搜索词进页后选对应份额下载 |")
lines.append(f"| 需核 | {sum(1 for r in funds if COV[r['name']]['status']=='需核')} | 家族在但所需份额未确认，进页后核对份额/币种 |")
lines.append(f"| 无 | {sum(1 for r in funds if COV[r['name']]['status']=='无')} | 多轮搜索未找到，investing 帮不上 |")
lines.append(f"| 不适用 | {sum(1 for r in funds if COV[r['name']]['status']=='不适用')} | 结构化票据/ETP，investing 无此产品 |")
lines.append("")

for cat in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    group = [r for r in funds if r["category"].split("/")[0] == cat]
    if not group:
        continue
    yes = [r for r in group if COV[r["name"]]["status"] in ("有", "需核")]
    no = [r for r in group if COV[r["name"]]["status"] in ("无", "不适用")]
    lines.append(f"### {cat}（{len(group)}，可下载 {len(yes)} / 无解 {len(no)}）")
    lines.append("")
    if yes:
        lines.append("**可下载：**")
        lines.append("")
        lines.append("| # | 基金名称 | 状态 | 搜索词 | investing 参考页 | 说明 |")
        lines.append("|---|---|---|---|---|---|")
        for i, r in enumerate(yes, 1):
            c = COV[r["name"]]
            s = search_url(c["term"])
            term = f"[{c['term']}]({s})" if s else "-"
            url = f"[打开]({c['url']})" if c["url"] else "-"
            lines.append(f"| {i} | {r['name']} | {c['status']} | {term} | {url} | {c['note']} |")
        lines.append("")
    if no:
        lines.append("**无解（investing 无此产品）：**")
        lines.append("")
        lines.append("| # | 基金名称 | 状态 | 说明 |")
        lines.append("|---|---|---|---|")
        for i, r in enumerate(no, 1):
            c = COV[r["name"]]
            lines.append(f"| {i} | {r['name']} | {c['status']} | {c['note']} |")
        lines.append("")

lines.append("## 三、与已有入口的配合")
lines.append("")
lines.append("- 本清单只覆盖 investing.com；FT Markets / fundinfo / wallstreet-online 的人工任务仍按 `2026-08-14_人工下载任务清单.md` 执行。")
lines.append("- investing 无解的 32 支（无 15 + 不适用 17）里，结构化/ETP 17 支只能靠基金公司官网/销售平台导出；其余 15 支真基金可试 fundinfo/wallstreet-online 补漏。")
lines.append("")
lines.append("## 四、机器可读文件")
lines.append("")
lines.append("- `01_数据/eip_investing_coverage.csv`：91 行（71 基金 + 20 非基金），含状态/搜索词/参考链接/说明。")

out = BASE / "03_文档" / "规划" / "2026-08-14_investing搜索词清单_手动下载.md"
out.write_text("\n".join(lines), encoding="utf-8")
print("written:", out)

from collections import Counter
print("status:", dict(Counter(COV[r["name"]]["status"] for r in funds)))
print("fund rows:", len(funds))