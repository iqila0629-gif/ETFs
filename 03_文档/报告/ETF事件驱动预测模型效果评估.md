# ETF事件驱动预测模型效果评估：今日ETF涨跌 → 明日ProFunds方向与平均回报

> 报告日期：2026-07-31
> 研究模型：ETF 事件驱动条件统计预测模型（今日 ETF 涨跌条件 → 明日 ProFunds 涨跌与平均回报）
> 数据：129 支 ProFunds + 19 支 ETF，7,219 个共同交易日（1997-10-30 ~ 2026-07-27）

---

## 一、模型定义

本模型不预测具体点位，而是按上司指示做条件统计：

> 假设 SPY 今天涨了、QQQ 今天涨了，用历史数据预测 ProFunds 明天是涨还是跌，涨跌平均回报是多少。

模型的输入是"今日 ETF 涨跌事件"，输出是：

1. 明日基金更可能涨还是跌
2. 明日上涨时的平均回报、明天下跌时的平均回报

信号不清晰时**不操作**，不强迫每天输出预测。

---

## 二、预测思路

1. 由 `combined_profunds_nav.csv` 计算 129 支基金日回报，与 `combined_etf_returns.csv` 的 19 支 ETF 日回报按日期对齐。
2. 定义触发条件（共 236 个）：
   - 单条件：每支 ETF 涨 / 跌 / 大涨≥1% / 大跌≤-1%（76 个）
   - 双条件：SPY×QQQ 双涨、双跌、涨跌分歧（8 个）
   - 一致性条件：多数 ETF 同向、全线涨跌
   - 幅度分档：0-0.5%、0.5-1%、1-2%、>2% 及负向对称档（152 个）
3. 对每个（基金，条件）组合，用历史事件日统计：
   - N：事件天数
   - P_up / P_down：明日上涨/下跌概率
   - Avg_up / Avg_down：明日为正/为负时的平均回报
   - 条件期望：全部事件日明日回报的平均值
4. 决策规则（严格版）：
   - N≥100 且 P_up≥55% 且 Avg_up≥0.2% → 预测涨
   - N≥100 且 P_down≥55% 且 Avg_down≤-0.2% → 预测跌
   - 其他 → 不操作
5. 输出公司 13 行标准格式 CSV，日期降序，`Daily Return (%)` 列存放触发日的实际次日回报，第 5 行 Average 即策略实际平均回报。

---

## 三、验证方法

### 3.1 Walk-forward 样本外验证

- 每个触发日只使用该日**之前**的历史统计量做决策，不用未来数据
- 五个时期：2009-2012 / 2013-2016 / 2017-2020 / 2021-2023 / 2024-2026
- 通过条件：全期 Average 达到 ±0.2%、全期交易数≥50、至少 3/5 段达标、每段交易数≥10

### 3.2 冻结模型最终样本外确认

- 只用 **2025-01-01 之前**的数据选组合（含 walk-forward 稳定性筛选）
- 选中组合在 **2025-2026** 冻结期内逐日预测
- 冻结期交易数≥10 且 Average 达到 ±0.2% 才算最终通过

---

## 四、预测结果

### 4.1 扫描与初筛

| 阶段 | 条件数 | 组合数 | 严格规则通过 |
|------|--------|--------|--------------|
| 单条件 | 76 | 9,804 | 306 |
| 双条件/一致性 | 8 | 1,032 | 5 |
| 幅度分档 | 152 | 19,608 | 773 |
| 合计评估 | 236 | 30,444 | 1,084 |

### 4.2 Walk-forward 稳定性结果

- 评估组合：1,084 个
- 通过稳定性筛选：**347 个**，覆盖 **76 支基金**
- 基金类型：反向基金 37 支、普通多头 20 支、杠杆多头 19 支
- 达标段数分布：3 段 191 个、4 段 120 个、5 段 36 个
- 全期 Average：正值 173 个、负值 174 个；中位数约 -0.20%，范围 -1.33% ~ +1.17%

### 4.3 冻结样本外（2025-2026）最终确认

- 用 2025 年前数据选中的组合：**198 个**
- 冻结期内继续达标：**150 个（通过率 75.8%）**
- 覆盖 **54 支基金**：反向 26 支、杠杆多头 18 支、普通多头 10 支
- 冻结期总触发次数：**4,439 次**
- 达标组合冻结期 Average 中位数 **+0.297%**，范围 -1.698% ~ +2.902%

### 4.4 冻结样本外表现最好的组合（按绝对 Average）

| 基金 | 条件 | 类型 | 交易数 | 方向准确率 | 冻结期 Average |
|------|------|------|--------|-----------|----------------|
| UJPSX | XLE_bin_-2_-1 | 反向 | 11 | 90.9% | +2.902% |
| UJPIX | XLE_bin_-2_-1 | 杠杆多头 | 14 | 85.7% | +2.443% |
| UOPIX | FXY_big_up | 杠杆多头 | 17 | 76.5% | +1.719% |
| UOPSX | FXY_big_up | 反向 | 17 | 76.5% | +1.718% |
| USPSX | FXY_big_up | 反向 | 17 | 76.5% | -1.698% |
| USPIX | FXY_big_up | 杠杆多头 | 17 | 76.5% | -1.688% |
| PMPSX | GLD_bin_lt-2 | 反向 | 29 | 65.5% | +1.399% |
| PMPIX | GLD_bin_lt-2 | 普通多头 | 29 | 65.5% | +1.388% |
| INPIX | FXY_bin_1_2 | 普通多头 | 13 | 53.8% | +1.383% |
| INPSX | FXY_bin_1_2 | 反向 | 13 | 53.8% | +1.373% |
| UCPIX | GLD_bin_lt-2 | 杠杆多头 | 20 | 75.0% | -1.280% |
| UHPSX | XLF_bin_lt-2 | 反向 | 15 | 53.3% | -1.220% |
| UGPSX | EEM_bin_lt-2 | 反向 | 21 | 38.1% | -1.213% |
| UHPIX | XLF_bin_lt-2 | 杠杆多头 | 15 | 53.3% | -1.211% |
| UGPSX | XLF_bin_lt-2 | 反向 | 15 | 60.0% | +1.192% |

### 4.5 预测文件

- 347 份标准 13 行预测 CSV：`analysis_results/event_study/predictions/`
- 全部通过 Average 达标自动校验
- 明细日志：`analysis_results/event_study/prediction_log.csv`

### 4.6 完整日频输出

底层数据本身就是日频：基金和 ETF 面板均按交易日一行（7,219 个交易日）。

为满足"每个交易日都有记录"的要求，另生成完整日频表：

| 文件 | 内容 |
|------|------|
| `analysis_results/event_study/daily_predictions_all_funds.csv` | 7,219 个交易日 × 129 支基金，每交易日一行；触发日填入实际次日回报，未触发日留空 |
| `analysis_results/event_study/daily_funds_summary.csv` | 76 支有触发基金的日频汇总：触发天数、方向准确率、Average |

完整日频表统计（同一基金的多条件触发日已按日期去重）：

- 76 支基金有触发记录，合计触发日单元格 71,087 个
- 68 支基金按合并口径的日频 Average 仍达到 ±0.2%
- 示例：UOPIX 日频触发 2,743 天，Average = +0.2585%

说明：之前生成的 347 份预测 CSV 是"每基金×每条件"的稀疏表，只有触发日有行；完整日频表把未触发日也保留为空行，两者口径不同，不要混用。

如何阅读预测 CSV 和完整日频表，见示例：[UOPIX预测示例_预测思路与CSV阅读指南.md](./UOPIX预测示例_预测思路与CSV阅读指南.md)。

---

## 五、效果评估

### 5.1 有效部分

- 决策全程无未来信息泄露，walk-forward 与冻结样本外口径一致
- 冻结样本外通过率 75.8%，说明筛选出的信号有相当部分在 2025-2026 延续
- 杠杆/反向基金和极端行情事件贡献最大，与项目前期"高波动环境信号更强"的结论一致
- 输出直接符合公司 13 行标准格式，可交给吕先生处理

### 5.2 局限与风险

| 局限 | 说明 |
|------|------|
| 极端事件样本小 | 表现最好的组合只有 11-29 次冻结期交易，存在运气成分 |
| 组合间高度重叠 | 同一事件同时触发多支基金/多个条件，347 个组合不是 347 个独立信号 |
| 未考虑交易成本 | 未扣申购费、赎回费、滑点和资金占用成本 |
| 1x 基金入选少 | 普通多头仅 10 支在冻结期达标，主战场仍是杠杆/反向基金 |
| 冻结期仅约 1.5 年 | 时间短，需后续继续跟踪验证 |
| 未做组合优化 | 目前是逐组合达标，未做资金分配和多信号集成 |

---

## 六、当前进度

已完成：

- 数据面板、单/双/幅度条件扫描
- Walk-forward 稳定性验证
- 347 份预测 CSV 生成
- 冻结模型最终样本外确认（150/198 达标）
- 本效果评估报告

未完成（收尾项）：

- 工作日报更新
- 正式交付归档（如将预测 CSV 归集到 `analysis_results/final_outputs/`）
- 如需上线：交易成本测算、多组合去重、资金分配方案

---

## 七、复现方式

```bash
python analysis_results/event_study/build_panel.py
python analysis_results/event_study/scan_single_events.py
python analysis_results/event_study/scan_pair_events.py
python analysis_results/event_study/scan_magnitude_bins.py
python analysis_results/event_study/walk_forward.py
python analysis_results/event_study/generate_predictions.py
python analysis_results/event_study/final_holdout.py
```

关键中间结果：

| 文件 | 内容 |
|------|------|
| `analysis_results/event_study/stable_combos.csv` | 347 个稳定组合 |
| `analysis_results/event_study/validation_summary.csv` | walk-forward 全组合结果 |
| `analysis_results/event_study/stability_report.csv` | 每组合 × 5 时期明细 |
| `analysis_results/event_study/holdout_report.csv` | 冻结样本外确认结果 |
| `analysis_results/event_study/predictions/` | 347 份标准格式预测 CSV |
| `analysis_results/event_study/daily_predictions_all_funds.csv` | 完整日频表（每交易日一行） |
| `analysis_results/event_study/daily_funds_summary.csv` | 基金级日频汇总 |
