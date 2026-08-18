# investing.com 覆盖判断与手动下载搜索词清单

> 日期：2026-08-17
> 方法：对 71 支待下载基金逐支做 `site:investing.com` 网页搜索判断覆盖，再给出 investing.com 站内搜索词供手动下载。
> 说明：只能判断『基金家族在不在 investing』，具体份额（ACC/DIS、USD/HKD）需进页核对。

## 一、怎么用

1. 打开 https://www.investing.com/ ，把『搜索词』粘进顶部搜索框，回车。
2. 在结果里选**与清单份额/币种一致**的那一条（如 A/USD/ACC），点进基金页。
3. 点 **Historical Data**（历史数据），把时间范围按年拉满，页面可导出 CSV（格式同你已下载的 `US Cotton #2 Futures Historical Data.csv`：`Date,Price,Open,High,Low,Vol.,Change %`）。
4. 保存为 `01_数据/人工下载/<基金名称>.csv`（文件名用清单里的名字即可），至少保留 `Date, Close`。

> ⚠️ 份额/币种务必核对：同名基金有 ACC/DIS、USD/HKD/EUR 等多个份额，只取清单要求的那一条；
> 拿不准就标记『份额待核』，不要拿不同份额冒充。

## 二、覆盖统计（71 支）

| 状态 | 数量 | 说明 |
|---|---|---|
| 有 | 32 | 基金家族已在 investing 确认，按搜索词进页后选对应份额下载 |
| 需核 | 7 | 家族在但所需份额未确认，进页后核对份额/币种 |
| 无 | 15 | 多轮搜索未找到，investing 帮不上 |
| 不适用 | 17 | 结构化票据/ETP，investing 无此产品 |

### AMERICAN（9，可下载 6 / 无解 3）

**可下载：**

| # | 基金名称 | 状态 | 搜索词 | investing 参考页 | 说明 |
|---|---|---|---|---|---|
| 1 | ABERDEEN STD - NORTH AMERICAN SMALLER COMPANIES FUND I ACC USD USD | 有 | [abrdn American Growth - Smaller Companies](https://www.investing.com/search/?q=abrdn%20American%20Growth%20-%20Smaller%20Companies) | [打开](https://au.investing.com/funds/aberdeen-american-growthsmaller-company-profile) | 页面标题即 Aberdeen Standard SICAV I - North American Smaller Companies；下载时核对 I ACC USD 份额 |
| 2 | ALLIANCE BERNSTEIN AMERICAN INCOME PORTFOLIO INC USD | 有 | [American Income Portfolio](https://www.investing.com/search/?q=American%20Income%20Portfolio) | [打开](https://www.investing.com/funds/american-income-portfolio-a2-ace-company-profile) | A2 Acc=0P000019TN；INC 份额选 A Income（持仓页可见 A Ine），核对份额/币种 |
| 3 | ALLIANCEBERNSTEIN AMERICAN INCOME USD | 有 | [American Income Portfolio S USD Acc](https://www.investing.com/search/?q=American%20Income%20Portfolio%20S%20USD%20Acc) | [打开](https://au.investing.com/funds/american-income-portfolio-s-usd-acc-scoreboard) | S USD Acc=0P00011R8T，ISIN LU0231611335；与上一条同家族不同份额 |
| 4 | CTMGMT LUX AMERICAN AU USD ACC USD | 需核 | [CT (Lux) American](https://www.investing.com/search/?q=CT%20%28Lux%29%20American) | [打开](https://se.investing.com/funds/lu1878469607-company-profile) | 家族已确认（American Smaller Companies 系列）；'American AU' 份额需核对 |
| 5 | FRANKLIN TEMPLETON LATIN AMERICA A ACC USD | 有 | [Templeton Latin America](https://www.investing.com/search/?q=Templeton%20Latin%20America) | [打开](https://hk.investing.com/funds/templeton-latin-americafund-aaccusd#1) | A(acc)USD=0P00000B0V，正好匹配 |
| 6 | JPMF A JPMF AMERICA EQUITY A USD USD | 有 | [JPMorgan America Equity](https://www.investing.com/search/?q=JPMorgan%20America%20Equity) | [打开](https://cn.investing.com/funds/jpmorgan-america-eq-fund-a-acc-usd-company-profile#1) | A (acc) USD=0P000019D5，正好匹配 |

**无解（investing 无此产品）：**

| # | 基金名称 | 状态 | 说明 |
|---|---|---|---|
| 1 | ARBROOK G10 AMERICAN EQUITIES A1 USD ACC USD | 无 | 多轮搜索未找到（Arbrook 为小众管理人） |
| 2 | CT MGMT AMERICAN 3U USD ACC USD | 无 | ISIN LU1864949380 investing 未收录；investing 只有 CT (Lux) American Smaller Companies 系列 |
| 3 | THREADNEEDLE LATIN AMERICAN NAV ACC USD | 无 | investing 无 Threadneedle Latin American（UK OEIC） |

### GLOBAL（60，可下载 33 / 无解 27）

**可下载：**

| # | 基金名称 | 状态 | 搜索词 | investing 参考页 | 说明 |
|---|---|---|---|---|---|
| 1 | AMUNDI BD GLOBAL AGG AUC 3D USD | 有 | [Amundi Funds Global Aggregate Bond](https://www.investing.com/search/?q=Amundi%20Funds%20Global%20Aggregate%20Bond) | [打开](https://se.investing.com/funds/amundi-global-aggreg-bond-a-usd-c-company-profile) | A USD (C)=0P0000A48C；清单里 'AUC 3D' 疑似其缩写，下载时核对份额 |
| 2 | ARTISAN PTNRS GBL GLOBAL OPPORTUNITIES I USD | 有 | [Artisan Global Opportunities](https://www.investing.com/search/?q=Artisan%20Global%20Opportunities) | [打开](https://ca.investing.com/funds/artisan-global-opportunities-inv-company-profile) | US 份额 ARTRX/APHRX、I EUR=0P0000X7XK 已确认；选 I USD 下载 |
| 3 | BLACKROCK (LUX) SA BGF GLOBAL INFL L A2 USD | 有 | [BlackRock Global Inflation Linked Bond](https://www.investing.com/search/?q=BlackRock%20Global%20Inflation%20Linked%20Bond) | [打开](https://www.investing.com/funds/global-inflation-linked-bond-fund-x-company-profile) | 家族已确认（E2/X2 等）；选 A2 USD 份额下载 |
| 4 | BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPP A2 USD USD | 有 | [BlackRock Fixed Income Global Opportunities](https://www.investing.com/search/?q=BlackRock%20Fixed%20Income%20Global%20Opportunities) | [打开](https://fi.investing.com/funds/blackrock-fixed-income-globl-opp-a2-company-profile) | A2=0P00008FSR；确认 USD 份额 |
| 5 | BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPPS D5 USD | 需核 | [BlackRock Fixed Income Global Opportunities D5](https://www.investing.com/search/?q=BlackRock%20Fixed%20Income%20Global%20Opportunities%20D5) | - | 家族已确认（A2/C2）；D5 USD 份额需在 investing 内核对 |
| 6 | FRANKLIN TEMP GLOBAL HI YLD MDIS \$ USD | 有 | [Franklin High Yield Fund](https://www.investing.com/search/?q=Franklin%20High%20Yield%20Fund) | [打开](https://uk.investing.com/funds/lu0889566138-user-rankings) | 家族已确认（N(Mdis)USD=0P0000Y5Q7）；选 A(Mdis)USD 份额下载 |
| 7 | FRANKLIN TEMP GLOBAL INC A ACC USD USD | 有 | [Templeton Global Income Fund](https://www.investing.com/search/?q=Templeton%20Global%20Income%20Fund) | [打开](https://hk.investing.com/funds/lu0976567544-company-profile) | 家族已确认（A(Mdis)SGD-H1=0P0000ZT9O）；选 A(acc)USD 份额下载 |
| 8 | FRANKLIN TEMPLETON FRANKLIN MUT GLOBAL DVRY A CAP USD | 有 | [Franklin Mutual Global Discovery](https://www.investing.com/search/?q=Franklin%20Mutual%20Global%20Discovery) | [打开](https://cn.investing.com/funds/franklin-mutual-global-discovery-a-company-profile) | US 份额 TEDIX/FMDRX 已确认；离岸 A(acc)USD 需核对 |
| 9 | FRANKLIN TEMPLETON GLOBAL TOTAL RETURN A MDIS USD USD | 有 | [Templeton Global Total Return](https://www.investing.com/search/?q=Templeton%20Global%20Total%20Return) | [打开](https://hk.investing.com/funds/t-global-total-return-fund-a-acc-us#1) | A(acc)USD=0P00000HPA 已确认；选 A(Mdis)USD 份额下载 |
| 10 | FRANKLIN TEMPLETON GLOBAL TOTAL RETURN FUN A ACC USD USD | 有 | [Templeton Global Total Return](https://www.investing.com/search/?q=Templeton%20Global%20Total%20Return) | [打开](https://hk.investing.com/funds/t-global-total-return-fund-a-acc-us#1) | A(acc)USD=0P00000HPA，正好匹配 |
| 11 | FTGF GBL BRANDYWNE GLOBAL FIXED INCOME A USD ACC USD | 有 | [FTGF Brandywine Global Fixed Income](https://www.investing.com/search/?q=FTGF%20Brandywine%20Global%20Fixed%20Income) | [打开](https://pt.investing.com/funds/fixed-income-fund-class-lm-ususd-ac-company-profile) | LM Class US$ Acc=0P0000Z6UY、Premier=0P0000RWW1 已确认；选 A Class US$ Acc 下载 |
| 12 | GLOBAL X FDS GBL X FTSE ARGENT USD USD | 有 | [Global X FTSE Argentina 20](https://www.investing.com/search/?q=Global%20X%20FTSE%20Argentina%2020) | [打开](https://cn.investing.com/etfs/global-x-ftse-argentina-20-historical-data?cid=1214670) | ARGT（美国 ETF）历史数据页可直接导出；确认币种/上市地 |
| 13 | GLOBAL X FDS GBL X ROBOTICS & ARTIFICIAL USD | 有 | [Global X Robotics & Artificial Intelligence](https://www.investing.com/search/?q=Global%20X%20Robotics%20%26%20Artificial%20Intelligence) | [打开](https://hk.investing.com/etfs/global-x-robotics---ai-usd#1) | BOTZ（美国）/ XB0T（UCITS，ISIN IE00BLCHJB90）；历史数据页可导出 |
| 14 | GUINNESS GAM GLOBAL EQUITY INCOME INC D USD | 有 | [Guinness Global Equity Income](https://www.investing.com/search/?q=Guinness%20Global%20Equity%20Income) | [打开](https://ph.investing.com/funds/guinness-global-equity-income-z-holdings) | Z/D/Y 份额已确认；选 D USD Inc 份额下载 |
| 15 | INVESCO MANAGEMENT GLOBAL EQUITY INCOME A USD ACC NAV USD | 有 | [Invesco Global Equity Income](https://www.investing.com/search/?q=Invesco%20Global%20Equity%20Income) | [打开](https://ca.investing.com/funds/gb00b8n46178#1) | UK Z Inc=0P0000XBQW、A AUD hedged 已确认；卢森堡 A USD Acc（LU0607513230）需核对 |
| 16 | INVESCO MANAGEMENT GLOBAL SMALL CAP EQUITY A USD | 有 | [Invesco Global Small Cap Equity](https://www.investing.com/search/?q=Invesco%20Global%20Small%20Cap%20Equity) | [打开](https://hk.investing.com/funds/invesco-european-small-company-a#1) | US ESMAX 已确认；卢森堡 A USD（LU1075211273）需核对 |
| 17 | iShares Macquarie Global Infra USD | 有 | [iShares Global Infrastructure UCITS](https://www.investing.com/search/?q=iShares%20Global%20Infrastructure%20UCITS) | [打开](https://www.investing.com/etfs/ishares-macquarie-global-inf.-100-holdings?cid=995525) | IDIN/INFR UCITS ETF USD (Dist)；历史数据可导出 |
| 18 | JPM IF GLOBAL DIVIDEND C ACC USD | 有 | [JPMorgan Global Dividend](https://www.investing.com/search/?q=JPMorgan%20Global%20Dividend) | [打开](https://cn.investing.com/funds/jpmorgan-invs-glbl-div-c-acc-usd#1) | C (acc) USD=0P0000XC5F，正好匹配 |
| 19 | JPMF AM GLOBAL EQUITY A DIST USD USD | 需核 | [JPMorgan Funds Global Equity](https://www.investing.com/search/?q=JPMorgan%20Funds%20Global%20Equity) | [打开](https://au.investing.com/funds/jpi-global-select-equity-fund-a-acu-company-profile#1) | 只确认到 Global Select Equity A(acc)USD=0P00000DS2（不同基金）；'Global Equity A dist USD' 需在 investing 内搜索核对 |
| 20 | JPMORGAN IF ASSET MGM GLOBAL BAL HGD A ACC USD USD | 有 | [JPMorgan Global Balanced](https://www.investing.com/search/?q=JPMorgan%20Global%20Balanced) | [打开](https://cn.investing.com/funds/jpi-global-balanced-fund-c-acc-usd#1) | C (acc) USD hedged=0P000115RQ 已确认；选 A (acc) USD hedged 下载 |
| 21 | JPMORGAN IF ASSET MGM GLOBAL INCOME HEDGED A USD ACC NAV USD USD | 有 | [JPMorgan Global Income](https://www.investing.com/search/?q=JPMorgan%20Global%20Income) | [打开](https://ms.investing.com/funds/jpi-global-income-fund-a-div-usd-he-company-profile) | A (div) USD hedged=0P0000V47Q 已确认；选 A (acc) USD hedged 下载 |
| 22 | JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS A HGD USD | 有 | [JPMorgan Global Macro Opportunities](https://www.investing.com/search/?q=JPMorgan%20Global%20Macro%20Opportunities) | [打开](https://ca.investing.com/funds/lu1181866309-scoreboard) | A (acc) USD hedged=0P00015EF8，正好匹配 |
| 23 | JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS C USD ACC USD | 有 | [JPMorgan Global Macro Opportunities C](https://www.investing.com/search/?q=JPMorgan%20Global%20Macro%20Opportunities%20C) | [打开](https://il.investing.com/funds/jpm-global-macro-opp-c-acc-eur-company-profile) | C (acc) EUR=0P00000DQ4 已确认；选 C (acc) USD 下载 |
| 24 | JPMORGAN IF GLOBAL INCOME C DIS HDG USD | 有 | [JPMorgan Global Income C](https://www.investing.com/search/?q=JPMorgan%20Global%20Income%20C) | [打开](https://hk.investing.com/funds/jpi-global-income-fund-d-mth-usd-he-holdings) | D (mth) USD hedged=0P0000X5GN 已确认；选 C (dis/div) USD hedged 下载 |
| 25 | JSS EMERGINGSAR GLOBAL A DIST USD | 需核 | [JSS Sustainable Equity Global](https://www.investing.com/search/?q=JSS%20Sustainable%20Equity%20Global) | [打开](https://cn.investing.com/funds/jss-oekosar-eq-glbl-p-eur-dist-company-profile) | Global Thematic P/I/M EUR 已确认；'Global A USD dist' 需核对（可能叫 JSS Sustainable Equity - Global A USD dist） |
| 26 | NATIXIS INTL (LUX) HARRIS ASSOCS GLOBAL EQUITY I ACC USD | 有 | [Harris Associates Global Equity](https://www.investing.com/search/?q=Harris%20Associates%20Global%20Equity) | [打开](https://il.investing.com/funds/natixisluxi-harrisassoc-glbleqragbp-company-profile) | 家族已确认（R/A GBP=0P00011SQN、P/A SGD、R/A EUR）；选 I/A USD 下载 |
| 27 | PICTET FUNDS GLOBAL MEGATREND SEL I USD ACC USD | 有 | [Pictet Global Megatrend Selection I USD](https://www.investing.com/search/?q=Pictet%20Global%20Megatrend%20Selection%20I%20USD) | [打开](https://hk.investing.com/funds/pimegatrend-selection-i-usd#1) | I USD=0P0000I3X7，正好匹配 |
| 28 | PICTET FUNDS GLOBAL MEGATREND SELECTION P ACC USD USD | 有 | [Pictet Global Megatrend Selection P USD](https://www.investing.com/search/?q=Pictet%20Global%20Megatrend%20Selection%20P%20USD) | [打开](https://cn.investing.com/funds/pictet-global-megatrend-selection-p-company-profile) | P USD 已确认；下载时核对份额 |
| 29 | PIMCOG GLOBAL ADVIS INCOME PU INC USD | 需核 | [PIMCO GIS Income Fund](https://www.investing.com/search/?q=PIMCO%20GIS%20Income%20Fund) | [打开](https://www.investing.com/funds/ie00bym81516#1) | E/Investor/Admin USD 份额已确认；'PU'=P USD Income 需核对 |
| 30 | PROSPER FDS SICAV GLOBAL MACRO I USD | 需核 | [Prosper Funds SICAV Global Macro](https://www.investing.com/search/?q=Prosper%20Funds%20SICAV%20Global%20Macro) | [打开](https://cn.investing.com/funds/prosper-stars-stripes-fund-i-eur-company-profile) | 同 SICAV 的 Stars & Stripes I EUR=0P00011MOB 已确认；Global Macro I USD 需核对 |
| 31 | SCHRODER INV MGMT QEP GLOBAL ACTIVE VAL A ACC USD USD | 有 | [Schroder QEP Global Active Value](https://www.investing.com/search/?q=Schroder%20QEP%20Global%20Active%20Value) | [打开](https://cn.investing.com/funds/schroder-qep-glblactive-value-i-acc-company-profile) | I Acc USD=0P000018N8 已确认；选 A Acc USD 下载 |
| 32 | VONTOBEL MGMT SA MIV GLOBAL MEDTECH P3 USD R USD | 有 | [MIV Global Medtech](https://www.investing.com/search/?q=MIV%20Global%20Medtech) | [打开](https://uk.investing.com/funds/variopartner-s-miv-global-medtech-u-company-profile) | P3 USD Cap=0P0000ZSTV，正好匹配 |
| 33 | VULCAN GLOBAL VALU VALUE EQUITY USD II INC NAV USD | 需核 | [Vulcan Value Equity](https://www.investing.com/search/?q=Vulcan%20Value%20Equity) | [打开](https://ph.investing.com/funds/ie00bc7gwl98-company-profile) | Vulcan Value Equity USD Inc=0P0000ZQWR 已确认；'II Inc' 份额需核对 |

**无解（investing 无此产品）：**

| # | 基金名称 | 状态 | 说明 |
|---|---|---|---|
| 1 | CAPITAL CITIGROUP GLOBAL MARKETS FUNDING MEMORY COUPON USD | 不适用 | 结构化票据，investing 无此产品 |
| 2 | CAUSEWAY BBVA GLOBAL QUAD INCOME USD | 不适用 | 结构化票据，investing 无此产品 |
| 3 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 3 USD | 不适用 | 结构化票据，investing 无此产品 |
| 4 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 4 USD | 不适用 | 结构化票据，investing 无此产品 |
| 5 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 7 USD | 不适用 | 结构化票据，investing 无此产品 |
| 6 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 8 USD | 不适用 | 结构化票据，investing 无此产品 |
| 7 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 9 USD | 不适用 | 结构化票据，investing 无此产品 |
| 8 | CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE USD | 不适用 | 结构化票据，investing 无此产品 |
| 9 | CAUSEWAY MORGAN STANLEY GLOBAL MARKETS INCOME NOTE USD | 不适用 | 结构化票据，investing 无此产品 |
| 10 | CELERITY GLOBAL BALANCED FUND IC A ACC USD | 无 | 未找到（只有 Celerius，非同一基金） |
| 11 | COMMERZBANK GLOBAL INDEX INCOME BUILDER 70-70 NOV 18 USD | 不适用 | 结构化票据，investing 无此产品 |
| 12 | FINCREST GLOBAL EQUITY FUND CLASS A USD | 无 | 未找到 |
| 13 | FRANKLIN TEMPL GLOBAL FOCUS FD A DIS USD | 无 | Franklin Global Focus 未找到 |
| 14 | FRANKLIN TEMPLETON GLOBAL FOCUS A ACC USD | 无 | Franklin Global Focus 未找到 |
| 15 | FTGF GBL W/A GLOBAL HIGH YIELD A USD ACC USD | 无 | Western Asset Global High Yield UCITS 未找到（investing 只有美国封闭式 EHI 与 FTGF 美国高收益） |
| 16 | IDAD NATIXIS GLOBAL INDICES AC JULY 2026 USD | 不适用 | 结构化票据，investing 无此产品 |
| 17 | IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC APRIL 2026 USD | 不适用 | 结构化票据，investing 无此产品 |
| 18 | IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC DEC 2025 USD | 不适用 | 结构化票据，investing 无此产品 |
| 19 | LEVERAGE VANILLA GLOBAL BALANCED INVESTMENT ETP USD | 不适用 | ETP，investing 无此产品 |
| 20 | MARIANA BBVA GLOBAL MARKETS MEMORY INCOME GENERATOR 8560 USD | 不适用 | 结构化票据，investing 无此产品 |
| 21 | MARIANA GLOBAL GROWTH KICK OUT NOTE V2 USD | 不适用 | 结构化票据，investing 无此产品 |
| 22 | MARIANA INVESTEC GLOBAL INDEX INCOME BUILDER 65 USD | 不适用 | 结构化票据，investing 无此产品 |
| 23 | NEUBERGER BERMN II GLOBAL SNR FTG RTE INC I US USD | 无 | 只有 NB Global Floating Rate（NBMI 封闭式，不同产品） |
| 24 | NG MORNINGSTAR GLOBAL DEFENSIV A USD ACC USD | 无 | 未找到 |
| 25 | NG MORNINGSTAR GLOBAL GROWTH A USD ACC USD | 无 | 未找到 |
| 26 | RUSSELL OLD MUTUAL VALUE GLOBAL EQUITY E ACC USD | 无 | Russell 家族（Multi-style/World Selection）在，但 Old Mutual Value 未找到 |
| 27 | RUSSELL OPENWORLD GLOBAL HIGH DIVIDEND EQUITY I USD | 无 | OpenWorld Global Listed Infrastructure=0P0000VV1E 在，但 Global High Dividend 未找到 |

### INTERNATIONAL（2，可下载 0 / 无解 2）

**无解（investing 无此产品）：**

| # | 基金名称 | 状态 | 说明 |
|---|---|---|---|
| 1 | MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL EQUITY FUND A USD ACCUMULATION USD | 无 | investing 无 Montlake/Quilter Cheviot 这两只基金 |
| 2 | MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL GROWTH FUND A USD ACCUMULATION USD | 无 | investing 无 Montlake/Quilter Cheviot 这两只基金 |

## 三、与已有入口的配合

- 本清单只覆盖 investing.com；FT Markets / fundinfo / wallstreet-online 的人工任务仍按 `2026-08-14_人工下载任务清单.md` 执行。
- investing 无解的 32 支（无 15 + 不适用 17）里，结构化/ETP 17 支只能靠基金公司官网/销售平台导出；其余 15 支真基金可试 fundinfo/wallstreet-online 补漏。

## 四、机器可读文件

- `01_数据/eip_investing_coverage.csv`：91 行（71 基金 + 20 非基金），含状态/搜索词/参考链接/说明。