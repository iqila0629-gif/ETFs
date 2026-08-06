# Adj Close 重跑与基金名展示计划

> 日期：2026-08-05
> 目的：把最终成果、失败版本两个交付文件夹全部更新为 Adj Close（总回报口径）版本，并把基金展示改为“基金名字（代码）”

---

## 一、背景

上司要求使用基金派息调整后的价格（Adj Close）。当前交付结果基于 Close/NAV（价格回报），
需要切换到 Adj Close（总回报）后重新执行，并评估结论是否变化。

已确认：

1. 失败版本也需要用 Adj Close 重跑各自版本（版本1 = 19 支 ETF；版本2 = 11 支精简版本）
2. 最终成果、失败版本两个交付文件夹里的**所有基金展示**都要改成“基金名字（代码）”，其他文件夹不改

---

## 二、阶段 0：修正 Adj 数据单位

- 现有管道所有回报都是百分数（-2.2 = -2.2%），上一轮生成的 Adj 表是小数
- 修正 `build_adj_close_tables.py`，把回报 ×100 后重新生成：
  - combined_profunds_adj_nav.csv（Adjusted NAV）
  - combined_profunds_adj_returns.csv
  - combined_etf_returns_adj.csv（19 支）
  - combined_extended_etf_returns_adj.csv（57 支）
  - panel_fund_returns_adj.csv / panel_etf_returns_adj.csv

## 三、阶段 1：基金名称映射

- 用 Nasdaq `/api/quote/{TICKER}/info?assetclass=mutualfunds` 批量抓 129 支基金名称
- 生成 `基金名称映射.csv`：基金代码、基金名字
- 展示格式：`基金名字（基金代码）`
- 映射表先放分析目录；确认交付后再放入两个交付文件夹

## 四、阶段 2：Adj Close 重跑（新文件夹 analysis_results/adj_close_v3/）

- 候选条件空间复用：17,779 个候选只依赖 ETF + 条件 + 窗口，不依赖数据口径，无需重新穷举
- 用 Adj 面板重建 master：
  - 基金：panel_fund_returns_adj.csv
  - 19 支 ETF：panel_etf_returns_adj.csv
  - 57 支 ETF：combined_extended_etf_returns_adj.csv
  - 外部数据：external_daily.csv（不变）
- 重新计算全部候选统计，按原规则筛选：
  - 全历史：|Average| ≥ 0.2%、交易数 ≥ 50、命中率 > 55%
  - 冻结期：|Average| ≥ 0.2%、交易数 ≥ 10、命中率 ≥ 55%
- 生成 v3 中间结果：候选统计、达标信号、每基金最佳、策略映射

## 五、阶段 3：评估结论是否变化（确认点）

对比 Close 口径 vs Adj Close 口径：

- 覆盖基金数
- 达标信号数
- 每基金最佳 Average / 命中率
- 失败版本结果是否仍失败、失败原因是否变化

结论变化不明显则按新结果交付；变化明显则列出差异说明，供确认。

## 六、阶段 4：更新两个交付文件夹（确认后执行）

- 最终成果：关键成果全部替换为 v3 输出，文件名不变
- 失败版本：两个版本关键结果用 Adj Close 重跑（版本1、版本2），文件名不变
- 数据文件夹此前已更新为 Adj Close 源数据
- 说明文档同步更新为“Adj Close 版本”

## 七、阶段 5：基金名字（代码）展示（确认后执行）

- 交付的两个文件夹里所有基金展示改为“基金名字（代码）”：
  - 普通表：基金代码列的值 → 名字（代码）
  - 公司格式表：129 个基金列头 → 名字（代码）
  - 信号列（如 UOPIX__XLY_lt-2）→ 名字（代码）__条件
- 其他文件夹（中间文档等）保持基金代码
- 说明 Sheet 注明展示规则

## 八、交付顺序与确认门

1. 新文件夹重跑完成
2. 输出 Close vs Adj Close 评估报告
3. 用户确认后再更新最终成果、失败版本
4. 基金名展示在更新交付文件夹时一并处理

## 九、产出

| 产出 | 位置 |
|------|------|
| Adj 数据表 | processed_returns/（*_adj.csv） |
| 基金名称映射 | analysis_results/adj_close_v3/基金名称映射.csv |
| v3 中间结果 | analysis_results/adj_close_v3/ |
| 对比评估报告 | analysis_results/adj_close_v3/Close_vs_AdjClose评估.md |
| 更新后的交付文件夹 | 最终成果 / 失败版本（确认后） |
