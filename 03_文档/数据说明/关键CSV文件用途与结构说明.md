# 关键 CSV 文件用途与结构说明

> v4 更新（2026-08-06）：正式建模只使用原始 19 支 ETF，扩展 ETF 已备份停用。
> 新增 v4 文件：`01_数据/processed_returns/v4_etf19_panel.csv`、
> `01_数据/processed_returns/v4_external_panel.csv`、
> `04_结果/v4_中间结果/v4_threshold_sensitivity.csv`、
> `04_结果/v4_中间结果/v4_19etf_baseline_pass.csv`。

> 更新日期：2026-08-03
> 当前正式口径：全历史 Average ≥ ±0.2% 且冻结期 Average ≥ ±0.2%、冻结期方向准确率 ≥ 55%

这份文档用大白话说明每个关键 CSV 是干什么的、里面长什么样、怎么看。

---

## 〇、先认识“公司 13 行格式”

很多 CSV 前 13 行是固定统计头，第 13 行以后才是数据：

| 行 | 内容 | 意思 |
|----|------|------|
| 1 | 空白 | 固定占位 |
| 2 | Hit Ratio | 上涨次数 / (上涨+下跌) |
| 3 | Up Count | 涨的次数 |
| 4 | Down Count | 跌的次数 |
| 5 | Average | 平均回报（**验收就看这里**） |
| 6-10 | Max/Min/Count/Std/Sum | 最大、最小、样本数、标准差、总和 |
| 11-12 | 空白 | 预留 |
| 13 | 列名 | 例如 `Date,Daily Return (%)` |
| 14+ | 数据 | 每天一行，日期降序 |

`skiprows=12` 就是跳过这 12 行统计头，直接从第 13 行列名开始读。

---

## 一、数据准备类

### 1. `processed_returns/combined_profunds_nav.csv`

- 用途：129 支 ProFunds 基金的**净值（NAV）**总表
- 结构：13 行统计头 + `Date` 列 + 129 个基金列（每支基金一列）
- 数据：7,241 个交易日，最新日期在最上面
- 注意：这是净值，不是回报；基金日回报由它算出来（`pct_change`）

### 2. `processed_returns/combined_etf_returns.csv`

- 用途：原始 19 支 ETF 的**日回报**总表
- 结构：13 行统计头 + `Date` + 19 个 ETF 列
- 数据：7,691 个交易日

### 3. `processed_returns/combined_extended_etf_returns.csv`

- 用途：新增 57 支扩展 ETF 的**日回报**总表
- 结构：同上，`Date` + 57 个 ETF 列
- 数据：2016-08 起约 10 年（Nasdaq 接口上限）
- 注意：没有 1999-2016 的历史，只能做近期验证

### 4. `processed_returns/extended_etf_returns/`

- 用途：57 支扩展 ETF，每支一个独立 13 行格式 CSV
- 文件名：`IEF.csv`、`TMF.csv` 等

### 5. `analysis_results/event_study/panel_fund_returns.csv` / `panel_etf_returns.csv`

- 用途：**建模用的干净面板**，没有 13 行头，只保留日期 + 数值
- 结构：`Date` + 基金/ETF 列，日期升序
- 注意：这里的回报是小数（0.01 = 1%），13 行格式文件里是百分数（1.00 = 1%）

### 6. `analysis_results/event_study/panel_quality_report.csv`

- 用途：每支基金有多少天数据、起止日期
- 结构：`ticker, obs, start, end`
- 用法：`obs < 1000` 属于短历史基金（如 ETHFX）

---

## 二、扫描与诊断类

### 7. `event_summary_single.csv` / `event_summary_pair.csv` / `event_summary_bins.csv`

- 用途：三种条件扫描的**全量统计表**
- 每个条件对每支基金一行，字段：
  - `n`：历史上条件出现次数
  - `p_up` / `p_down`：明天上涨/下跌概率
  - `avg_up` / `avg_down`：明天涨时/跌时的平均回报（%）
  - `expected`：条件期望回报（%）
- 用法：先看这张表找候选，再看后面验证表确认

### 8. `shortlist_single.csv` / `shortlist_pair.csv` / `shortlist_bins.csv`

- 用途：初筛短名单（N 够、概率有偏向、期望够大），研究用
- 注意：不是最终达标名单

### 9. `target_funds_diagnosis.csv`

- 用途：之前“空白/稀疏基金”的诊断：每支基金样本量、波动率、最匹配 ETF、最佳条件

### 10. `fund_etf_fit_matrix.csv`

- 用途：**129 支基金 × 76 支 ETF 的完整契合度表**
- 字段：`Same`（同日相关性）、`Lead1`（领先 1 日相关性）、`DirAgree`（方向一致性）、`has_dual_signal`（是否产生正式信号）
- 用法：想看“这支基金和哪支 ETF 关系最紧密”就看 `Same` 最大的行

### 11. `etf_effectiveness.csv`

- 用途：**每支 ETF 对多少支基金产生了正式信号**
- 字段：`ETF, effective_funds, suggestion`
- 用法：`effective_funds = 0` → 建议删除（当前只有 LQD、JNK）

---

## 三、验证类

### 12. `stable_combos.csv`

- 用途：主模型 walk-forward 验证后通过的组合（347 个，旧口径）
- 字段：`ticker, condition, overall_trades, overall_avg, periods_passed`

### 13. `holdout_report.csv`

- 用途：主模型候选的**冻结样本外（2025-2026）确认**
- 字段：`selected`（2025 前选中？）、`holdout_avg`、`holdout_pass`

### 14. 专项各阶段验证表

| 文件 | 验证什么 |
|------|----------|
| `sparse_relaxed_validation.csv` | 放松阈值信号 |
| `mapping_composite_validation.csv` | ETF 映射/复合信号 |
| `multi_day_validation.csv` | 2/3/5 日窗口信号 |
| `self_signal_results.csv` | 基金自身涨跌信号 |
| `external_signal_results.csv` | VIX/TNX 信号 |
| `extended_etf_validation.csv` | 57 支新 ETF 单条件 |
| `blank_funds_more_etf_validation.csv` | 空白基金补充扫描 |
| `gap_funds_targeted_validation.csv` | 最后 6 支缺口基金专门扫描（结果 0 达标） |

这些表的结构类似：`ticker, condition, selection_*, holdout_*, pass_and_reliable`。

### 15. `optimization_scan.csv`

- 用途：57 支新 ETF 对全部基金的**优化扫描**（16,855 个候选）
- 用法：配合 `optimization_summary_unified.csv` 看每支基金新旧信号对比
- 注意：扫描结果还要经过双口径重筛才进入正式名单

---

## 四、双口径正式类（最常用）

### 16. `dual_criteria_pass.csv`

- 用途：**当前正式达标信号总表（3,014 个）**
- 每个信号必须同时满足：
  - 全历史 |Average| ≥ 0.2%、交易数 ≥ 50
  - 冻结期 |Average| ≥ 0.2%、交易数 ≥ 10、方向准确率 ≥ 55%
- 字段：`ticker, source, condition, horizon, full_avg, full_trades, frozen_avg, frozen_trades, frozen_hit, dual_pass`
- 旧 45% 门槛版本备份在 `dual_criteria_pass_hit45_backup.csv`

### 17. `dual_criteria_summary.csv`

- 用途：**每支基金只保留 1 个最佳信号**（120 行）
- 用法：想做“每支基金一条策略”就直接看这个

### 18. `final_outputs_dual_full_history/`（3,014 份）

- 用途：正式预测 CSV，**全历史版本**
- 每个文件名：`基金代码__条件__N窗口.csv`
- 每份都是公司 13 行格式，第 5 行 Average 已达标

### 19. `final_outputs_dual_frozen/`（3,014 份）

- 用途：正式预测 CSV，**只保留 2025-2026 冻结期**，验收时优先看这个
- 结构和全历史版一样，只是数据行更短

### 20. `boss_criterion_full_history_pass.csv`

- 用途：早期按“只看全历史”口径的达标清单（主 347 + 专项 43），研究参考
- 现已被 `dual_criteria_pass.csv` 取代

---

## 五、合并规则与日频类

### 21. `merged_signal_days.csv`

- 用途：每支基金每天触发几个信号、方向是否冲突
- 字段：`n_signals, n_up, n_down, conflict` + 四种规则的方向/预测值

### 22. `merged_rule_evaluation.csv`

- 用途：四种合并规则（去重单记/冲突跳过/多数投票/取最强）分别算双口径达标数
- 结论：R4 取最强，基金级 51/120 达标

### 23. `daily_merged_R4_all_funds.csv`

- 用途：**基金级日频总表**，用 R4 合并后的最终日频结果
- 结构：13 行统计头 + `Date` + 129 基金列；有值=当天该基金出手，空白=不操作

### 24. `merged_R4_funds_summary.csv`

- 用途：基金级 R4 汇总（触发天数、方向准确率、Average）
- 注意：基金级合并后只有 51/120 整体达标；正式交付请用 `final_outputs_dual_*` 的单条件文件

### 25. 历史参考日频表

| 文件 | 说明 |
|------|------|
| `daily_predictions_all_funds_combined.csv` | 旧口径（45%）的主模型+专项合并表 |
| `daily_sparse_predictions_all_funds.csv` | 旧口径冻结期专项表 |
| `daily_predictions_all_funds.csv` | 主模型日频表 |

这些仅作历史参考，当前正式汇总以 `daily_merged_R4_all_funds.csv` 为准。

---

## 六、怎么看一个预测 CSV 的例子

以 `UOPIX__FXY_big_up.csv` 为例：

```text
Hit Ratio,0.618321      ← 61.8% 的日子方向正确
Average,0.755959        ← 出手日次日实际平均回报 +0.76%（达标）
...
Date,Daily Return (%)
04/30/2026,1.873699     ← 04/30 FXY 大涨触发，05/01 UOPIX 实际 +1.87%
```

“Date”是触发日，“Daily Return (%)”是**次日的实际回报**，不是预测值。没出现的日期 = 没触发 = 不操作。

---

## 六·一、公司整合表（正式交付推荐）

以下 4 张表都是**公司 13 行标准格式**，一列一支基金（129 列，未覆盖基金整列空白），每交易日一行、日期降序：

| 文件 | 内容 | 说明 |
|------|------|------|
| `company_daily_best_full_history.csv` | 最佳信号 · 全历史 | 每支基金只用 1 个最佳条件，120 列全历史 Average 全部 ≥ ±0.2% |
| `company_daily_best_frozen.csv` | 最佳信号 · 冻结期 | 同上，只保留 2025-2026，120 列全部达标 |
| `company_daily_all_signals_full_history.csv` | 全信号 · 全历史 | 每支基金的全部正式信号合并，同日冲突按“取最强”处理 |
| `company_daily_all_signals_frozen.csv` | 全信号 · 冻结期 | 同上，只保留 2025-2026 |

配套文件：

| 文件 | 内容 |
|------|------|
| `company_strategy_mapping.csv` | 每支基金用了哪个最佳条件、窗口、两个时期的 Average |
| `company_signal_detail_full_history.csv` | 全信号逐日明细（基金、条件、窗口、日期、预测值、实际值） |
| `company_signal_detail_frozen.csv` | 全信号逐日明细（只保留 2025-2026） |

### 怎么选

- 想直接交给吕先生：看 `company_daily_best_*`，每支基金一列、每列都达标
- 想看所有信号合起来的效果：看 `company_daily_all_signals_*`，但注意全历史合并后只有 53/120 支基金整体 Average 达标（弱信号稀释强信号），这是参考视图
- 想追某个信号具体哪天触发：看 `company_signal_detail_*`
- 想查每支基金对应什么策略：看 `company_strategy_mapping.csv`

---

## 七、使用建议

1. 交付给吕先生：用 `final_outputs_dual_frozen/` 或 `final_outputs_dual_full_history/`
2. 要每基金一条策略：用 `dual_criteria_summary.csv`
3. 要日频总表：用 `daily_merged_R4_all_funds.csv`
4. 要解释为什么某信号入选：用 `dual_criteria_pass.csv` 看两个口径的 Average
5. 要看 ETF 有没有用：用 `etf_effectiveness.csv`
