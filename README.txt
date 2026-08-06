准备转移 README
==============

一、这是什么
------------

本文件夹整理了一个“ProFunds 基金日频预测”项目从 event_study 阶段开始
最有用的数据、脚本、文档和最终成果，用于开启新任务时快速接手。

项目目标：
- 用 ETF 当日行情（含扩展ETF和外部数据）预测 ProFunds 基金未来 1/2/3 日方向；
- 只保留满足“全历史 + 冻结期”双口径且命中率门槛的正式信号；
- 为每支基金选一条最佳策略，并输出公司 13 行格式成果。

二、文件夹结构
--------------

准备转移/
├─ README.txt
├─ 01_数据/
│  ├─ processed_returns/          Adj Close 口径处理后合并 CSV
│  └─ event_study_inputs/         候选池、面板、相关性等底稿
├─ 02_脚本/
│  ├─ event_study/                event_study 阶段全部 Python 脚本
│  ├─ adj_close_v3/               Adj Close 重跑与 ETF 精简脚本
│  └─ standard_v2_legacy/         旧版 Excel 转换与校验辅助脚本
├─ 03_文档/
│  ├─ 项目要求/
│  ├─ 规划/
│  ├─ 数据说明/
│  ├─ 报告/
│  └─ 评估/
└─ 04_结果/
   └─ 最新成果/                    最终交付成果，包含数据、说明和中间文档

最终数据都在 04_结果/最新成果/数据/，不需要再另找原始数据。

三、数据从哪来
--------------

1. 原始 19 支 ETF
   - 来源：Yahoo Finance 日线。
   - 字段：Date、Open、High、Low、Close、Volume、Adj Close。

2. 扩展 57 支 ETF
   - 最初尝试 ETFDB，但页面 JS 渲染、部分数据付费，拿不到。
   - 最终使用 Yahoo v8 chart API。
   - 注意：v8 API 默认返回月频，必须显式指定 period1/period2 才能拿到日频。
   - 扩展 ETF 列表见 03_文档/规划/扩展ETF清单.md。

3. ProFunds 基金
   - 来源：Nasdaq 基金历史 JSON。
   - 关键参数：assetclass=mutualfunds。
   - 每个基金一个 JSON，取 Adjusted Close。

4. 外部数据
   - VIX、TNX、信用利差、股债相关性等，存放在 external_daily.csv。

5. 为什么用 Adj Close
   - Adj Close 是分红/拆股调整后的价格，等于总回报口径。
   - 上司要求使用 Adj Close，不能用普通 Close。

四、数据处理口径
----------------

1. 基金：
   - Adjusted Close 转成 Adjusted NAV。
   - 日回报面板用小数，0.01 = 1%。

2. ETF：
   - Adj Close 转成日回报。
   - 回报面板用百分数。

3. 合并：
   - 按 Date 对齐基金、19支ETF、57支扩展ETF、外部数据。

4. 13 行格式：
   - 公司要求的表格格式：前10行统计头 + 空2行 + 第13行列名 + 数据。
   - 统计头包括 Hit Ratio、Up Count、Down Count、Average、Max、Min、
     Count、Std、Sum。
   - 最终 Excel 中这些统计头用公式，不写死。

五、信号构造
------------

第一层：单条件/外部/自身
1. ETF 涨、跌、涨跌超过1%、涨跌超过2%。
2. 幅度分档：0-0.5%、0.5-1%、1-2%、>2%，以及负向对称档。
3. VIX/TNX 外部条件。
4. 基金自身涨跌、连续三日同向。

第二层：双条件穷举
1. 76 支 ETF 两两组合：2,850 对。
2. 每对 4 种方向：双涨、双跌、一涨一跌、一跌一涨。
3. 每个方向 1/2/3 日窗口。
4. 对 129 支基金逐一统计。

条件命名：
- ETF_up / ETF_down
- ETF_big_up / ETF_big_down
- ETF_gt2 / ETF_lt-2
- ETF_bin_0_0.5
- A_up_B_down
- ext_vix_chg_ge5
- self_3down

六、防未来信息与决策规则
------------------------

1. 每个触发日只用该日之前的历史统计做决策。
2. 对每个信号先统计：
   - 事件数
   - 上涨概率 p_up
   - 下跌概率 p_down
   - 上涨日平均回报 avg_up
   - 下跌日平均回报 avg_down
3. 常规信号门槛：
   - 累计事件数 >= 100
   - p_up >= 52% 且 avg_up >= 0.15% → predict_up
   - p_down >= 52% 且 avg_down <= -0.15% → predict_down
4. 主模型源更严格：
   - p >= 55%，avg >= 0.2%。

七、正式验收口径
----------------

全历史：
- |Average| >= 0.2%
- 交易数 >= 50
- 命中率 > 55%

冻结期（2025-2026）：
- |Average| >= 0.2%
- 交易数 >= 10
- 命中率 >= 55%

两个口径必须同时通过。

七点五、执行窗口口径（上司已确认）
----------------------------------

上司确认口径：
- 假设今天是 8/1，预测明天 8/2；
- SPY 8/1 回报 = 8/1收盘 / 7/31收盘 - 1；
- QQQ 8/1 回报同理；
- 用 8/1 的 ETF 回报预测基金 8/2 回报 =
  8/2收盘 / 8/1收盘 - 1。

当前实现与这个口径一致：
- 信号用 T 日（8/1）ETF/外部数据；
- 目标回报取 T+1 日（8/2）基金回报；
- 回报归属“8/2这一天”，8/1收盘只作为计算8/2波动的基准。

实盘执行提醒：
口径上我们没做错；但实盘是否能在8/1收盘完成买入，
仍然取决于基金下单截止时间和实时信号获取，属于执行层问题。

八、每基金最佳策略
------------------

选择优先级：
1. |全历史 Average| 最大
2. 冻结期命中率最高
3. 全历史命中率最高

注意：
- 这个规则是“Average优先”，不是“命中率优先”。
- 所以全部ETF的命中率中位数可能低于精简版。
- 原因是 ETF 越多，可能出现 Average 更大但命中率更低的信号。

九、全信号 R4 合并
------------------

同一基金同一天触发多个正式信号时：
- 只保留一条记录；
- 取 |全历史 Average| 最大的信号；
- 不叠加、不平均、不做多数投票；
- 未触发日留空。

R4 合并表只用于观察，不作为验收。

十、ETF 精简
------------

原则：
- 没有任何 ETF 是必须保留的；
- 一切由数据决定。

方法：
- 在现有正式信号池上按 ETF 子集重新选每基金最佳策略；
- 空集正向贪心；
- 76 支反向淘汰；
- 200 次随机重启。

选择标准：
- 覆盖 119 支基金；
- 全历史 Average 中位数 >= 0.50%；
- 冻结期 Average 中位数 >= 0.50%；
- 满足上述条件时优先减少 ETF 数量、提高命中率。

结果：
- 推荐 27 支 ETF；
- 可选清单 14-35 支，见最新成果/精简ETF。

十一、三个版本
--------------

全部ETF：76 支，48,854 个信号，覆盖 119 支基金。
精简ETF：27 支，7,386 个信号，覆盖 119 支基金。
原始ETF：19 支，2,960 个信号，覆盖 100 支基金。

指标均为“每支基金最佳策略”口径，不是 R4 合并口径。

十二、关键脚本
--------------

1. 数据处理
   - 02_脚本/standard_v2_legacy/build_adj_close_tables.py
   - 02_脚本/event_study/build_panel.py

2. 候选扫描
   - 02_脚本/event_study/scan_single_events.py
   - 02_脚本/event_study/scan_pair_events.py
   - 02_脚本/event_study/scan_magnitude_bins.py
   - 02_脚本/adj_close_v3/expand_pair_scan.py
   - 02_脚本/adj_close_v3/scan_original19_pair.py

3. 正式筛选与生成
   - 02_脚本/event_study/phase9_dual_criteria_pipeline.py
   - 02_脚本/adj_close_v3/run_v3.py
   - 02_脚本/adj_close_v3/build_v3_delivery.py

4. ETF 精简
   - 02_脚本/adj_close_v3/run_etf_streamline.py
   - 02_脚本/adj_close_v3/build_streamlined_delivery.py

5. 原始ETF版本
   - 02_脚本/adj_close_v3/build_original19_standard.py

6. 最终交付转换
   - 02_脚本/adj_close_v3/build_final_delivery.py
   - 02_脚本/adj_close_v3/build_final_data.py

7. 校验
   - 02_脚本/adj_close_v3/verify_v3_delivery.py
   - 02_脚本/adj_close_v3/verify_final_delivery.py

十三、复现顺序
--------------

1. 准备数据
   - 跑 build_adj_close_tables.py 生成 Adj Close 合并表和面板。

2. 生成候选
   - 跑 phase9_dual_criteria_pipeline.py 生成早期候选池。
   - 跑 run_v3.py 在 Adj Close 口径下重算。
   - 跑 expand_pair_scan.py 生成双条件候选。

3. 生成全部ETF成果
   - 跑 build_v3_delivery.py。

4. 生成精简ETF成果
   - 跑 run_etf_streamline.py。
   - 跑 build_streamlined_delivery.py。

5. 生成原始ETF成果
   - 跑 scan_original19_pair.py。
   - 跑 build_original19_standard.py。

6. 转最终交付格式
   - 跑 build_final_delivery.py。
   - 跑 build_final_data.py。

7. 校验
   - 跑 verify_v3_delivery.py。
   - 跑 verify_final_delivery.py。

十四、常见坑与经验
------------------

1. ETFDB 拿不到数据
   - JS 渲染、付费墙；不要浪费时间。
   - 直接换 Yahoo Finance v8 chart API。

2. Yahoo CSV 下载 401
   - 不要用 CSV 下载接口，改用 v8 chart API。

3. v8 API 默认月频
   - 必须显式指定 period1/period2，否则拿不到日频。

4. 必须用 Adj Close
   - 普通 Close 不含分红，不是总回报口径。

5. 基金和 ETF 回报单位不同
   - 基金面板用小数，ETF 面板用百分数。
   - 统计时基金回报要乘 100。

6. 多日窗口口径要一致
   - 单条件池允许“有几天算几天”；
   - 双条件池要求未来 N 天全部有数据。
   - 两种口径不能混用，否则统计对不上。

7. 76 支 ETF 的位掩码超过 64 位
   - 不能直接用 int64 位掩码。
   - 拆成低64位和高12位两个 uint64 数组。

8. 排序后的位置和原始位置不能混用
   - 之前出现过“用排序后的位置去原始 DataFrame 取行”的错误。
   - 取最佳策略行时，必须从排序后的表取。

9. 中位数口径要标清楚
   - 所有版本对照表都是“每支基金最佳策略”口径。
   - R4 合并后的表现会被弱信号稀释，不能混为一谈。

10. Excel 公式
   - openpyxl 只写公式，不计算结果；
   - 用 Excel 打开后会自动计算。

11. 旧版本不要随便删
   - 原口径/旧版14支都备份在 analysis_results/adj_close_v3/backup_*。

十五、交付成果怎么读
--------------------

1. 三个版本都在 04_结果/最新成果/。
2. 每支基金怎么操作：
   - 看 对应版本/成果/每基金策略映射.xlsx。
3. 每支基金历史表现：
   - 看 对应版本/成果/公司格式_最佳策略_全历史.xlsx。
4. 冻结期验收：
   - 看 对应版本/成果/公司格式_最佳策略_冻结期.xlsx。
5. ETF 数量取舍：
   - 看 精简ETF/成果/ETF规模影响_可选清单.xlsx。
6. 行列含义：
   - 每个 Excel 都有“说明”Sheet1 +“数据”Sheet2。

十六、新项目建议
----------------

1. 先读 03_文档/项目要求/00_项目要求.txt 和 数据爬取方法详细指导.md。
2. 先看 04_结果/最新成果/最新成果说明.txt。
3. 需要重跑时，按“十三、复现顺序”执行。
4. 遇到数据源问题时，直接参考“十四、常见坑与经验”。

十七、近期口径问答
------------------

1. Average 是回报率，不是价格。
   例如 3.625783 表示 +3.625783%。

2. 回报是“隔天”，不是“当天”。
   信号 T 日触发，窗口1日取 T+1 日回报；
   等价于 T 日收盘买入、T+1 日收盘卖出。

3. 窗口 N 日 = 未来 N 个交易日回报率的平均值。
   例如窗口3，T日触发，实际回报 = (T+1 + T+2 + T+3)/3。

4. 窗口在哪里看？
   - 每基金策略映射.xlsx：预测窗口（日）列。
   - 正式信号明细_全量.xlsx：预测窗口（日）列。
   - 信号逐日明细_最佳策略.xlsx：预测窗口（日）列。
   - 公司格式宽表：列名只显示基金，不显示窗口；
     需要到每基金策略映射.xlsx查该基金对应窗口。

5. 公司格式宽表里的值是什么？
   是触发日对应的未来回报率，不是NAV，也不是当天基金涨跌幅。

6. 命中率怎么算？
   预测上涨且未来回报 >0，或预测下跌且未来回报 <0，算命中。

7. 版本对照表的指标是什么口径？
   每支基金最佳策略口径，不是R4全策略合并口径。

8. 为什么全部ETF命中率中位数可能低于精简版？
   因为最佳策略排序是 Average优先；
   ETF变多后会引入Average更大但命中率更低的信号，
   全部ETF可能选到这些信号，导致中位数降低。

9. 当前回测能否直接实盘？
   不能。当前假设“T日收盘买入”，实盘需要解决信号时点与基金截止时间；
   口径已按上司确认；实盘执行时点仍需单独处理，
   详见“七点五、执行窗口口径（上司已确认）”。
