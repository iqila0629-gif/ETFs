# ETF 今日涨跌 → ProFunds 明日回报：事件研究

> 生成日期：2026-07-31
> 依据：上司指示——"假设 SPY 今天涨了、QQQ 今天涨了，用历史数据预测 ProFunds 明天是涨还是跌，涨跌平均回报是多少"

---

## 一、流程

按顺序运行：

```bash
python analysis_results/event_study/build_panel.py
python analysis_results/event_study/scan_single_events.py
python analysis_results/event_study/scan_pair_events.py
python analysis_results/event_study/scan_magnitude_bins.py
python analysis_results/event_study/walk_forward.py
python analysis_results/event_study/generate_predictions.py
```

## 二、输入与中间文件

| 文件 | 说明 |
|------|------|
| `panel_fund_returns.csv` | 129 支基金日回报，7,219 个共同交易日 |
| `panel_etf_returns.csv` | 19 支 ETF 日回报，与基金表按日期对齐 |
| `panel_quality_report.csv` | 每支基金样本量、起止日期 |
| `event_summary_single.csv` | 76 个单条件 × 129 支基金统计（9,804 行） |
| `event_summary_pair.csv` | 8 个 SPY×QQQ / 一致性条件 × 129 支基金 |
| `event_summary_bins.csv` | 152 个幅度分档条件 × 129 支基金 |
| `shortlist_*.csv` | 初筛：N≥200、\|期望\|≥0.15%、概率≥53% |
| `stability_report.csv` | 每个组合 × 5 个时期的样本外表现 |
| `validation_summary.csv` | 全部组合的总体样本外表现 |
| `stable_combos.csv` | 通过稳定性筛选的组合（347 个） |
| `prediction_log.csv` | 每个触发日的决策、预测值、实际回报 |

## 三、统计口径

对每个（基金，条件）组合：

- 事件日：ETF 满足条件的交易日
- 明日回报：事件日次一交易日的基金日回报
- P_up / P_down：明日上涨/下跌占比
- Avg_up / Avg_down：明日为正/为负时的平均回报（%）
- 条件期望：全部事件日明日回报的平均值（%）

决策规则（严格版）：

- N≥100 且 P_up≥55% 且 Avg_up≥0.2% → 预测涨
- N≥100 且 P_down≥55% 且 Avg_down≤-0.2% → 预测跌
- 其他情况 → 不操作

## 四、样本外验证

walk-forward 方式：每个事件日只用该日之前的历史统计量做决策，不使用未来数据。

通过条件：

- 全期实际回报 Average 达到 +0.2% / -0.2%
- 全期交易数 ≥ 50
- 5 个时期（2009-2012 / 2013-2016 / 2017-2020 / 2021-2023 / 2024-2026）中至少 3 段达标，每段交易数 ≥ 10

## 五、当前结果

- 评估组合：1,084 个
- 通过稳定性筛选：347 个
- 生成的预测 CSV：347 份，全部通过 Average 达标自动校验
- 输出目录：`predictions/`，文件名为 `基金代码__条件.csv`

输出为公司 13 行标准格式，日期降序，`Daily Return (%)` 列存放触发日的实际次日回报，第 5 行 Average 即该策略的实际平均回报。

## 六、重要提醒

1. 当前短名单先用全量数据筛选，再做 walk-forward 验证，存在一定的选择偏差。上线前应再冻结一轮模型（例如只用 2024 年底前数据选组合，再用 2025-2026 数据做最终样本外确认）。
2. 347 个组合之间高度重叠（同一 ETF 大涨大跌事件同时触发多个基金/条件），不能把它们当作独立信号。
3. 1x 基金很少入选，入选者多为杠杆/反向/高波动基金。
4. 输出文件只记录"应该操作"的日子；不操作的日子不输出，避免强迫预测。
