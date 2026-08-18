# EIP 新项目 Phase 1-3 报告（原始 19 ETF 预测，单条件版）

> 日期：2026-08-14　范围：仅单条件（19 ETF × 6 方向 × horizon 1/2/3）

## 一、干净子集筛选（Phase 0.5）
- 输入：`01_数据/eip_confirmed.csv`（133 条已确认）。
- 规则：① 仅 MUTUALFUND；② 同 symbol 只保留最优一条；③ 历史 ≥120 交易日；④ overlap ≥0.7；⑤ 排除货币基金（MONEY）。
- 干净目标：**56 支**（GLOBAL 53 / AMERICAN 2 / INTERNATIONAL 1）。
- 剔除留档：77 条 → `01_数据/eip_clean_excluded.csv`（含剔除原因）。
- 产物：`01_数据/eip_clean_targets.csv`、`eip_clean_excluded.csv`。

## 二、数据下载、清洗与面板（Phase 1）
- 下载：Yahoo v8 chart，**56/56 成功**；币种全部 USD（1 支 HKD：ALLIANZ GLOBAL INV HKD INCOME）；行数 235–5940。
- 清洗：复用 v4 尖峰/断层修复，共 12 处修复（均在 SCHRODER INTL SEL GLOBAL GOLD A）。
- 面板：`01_数据/新项目_processed/eip_panel_19etf.csv`，7700 行（1996-01-02 .. 2026-08-07），56 基金列（回报=小数）+ 19 ETF 列（回报=百分数），无未来函数（T 日信号→T+1 回报）。
- 备注：ETF 日历沿用 v4 `panel_etf_returns_adj.csv`（截至 2026-08-07），基金原始数据到 08-13/14；如需最新窗口需先刷新 ETF 面板。

## 三、单条件扫描（Phase 2）
- 条件空间：19 ETF × {up, down, big_up, big_down, gt2, lt-2} × horizon {1,2,3} = 342 个 条件×horizon。
- 候选池：**7290 条**信号（53 支基金至少 1 条）；3 支（Morgan Stanley IF 系列，历史仅 235 行）因单条件无法凑满决策窗口而无信号。
- 产物：`eip_single_pass.csv`（全历史/冻结期统计 + pass 标记）。

## 四、合规筛查与门槛敏感性（Phase 3）
- 双口径：全历史 + 冻结期（2025-01-01 起）；命中率 ≥55%、|Average| ≥0.2%。
- 敏感性（full_min × frozen_min）：
  - full≥50 / frozen≥10：信号 413 条，覆盖 35 支。
  - full≥50 / frozen≥15：信号 413 条，覆盖 35 支。
  - full≥50 / frozen≥20：信号 413 条，覆盖 35 支。
  - full≥50 / frozen≥30：信号 411 条，覆盖 35 支。
  - full≥80 / frozen≥10：信号 409 条，覆盖 35 支。
  - full≥80 / frozen≥15：信号 409 条，覆盖 35 支。
  - full≥80 / frozen≥20：信号 409 条，覆盖 35 支。
  - full≥80 / frozen≥30：信号 409 条，覆盖 35 支。
  - full≥100 / frozen≥10：信号 408 条，覆盖 35 支。
  - full≥100 / frozen≥15：信号 408 条，覆盖 35 支。
  - full≥100 / frozen≥20：信号 408 条，覆盖 35 支。
  - full≥100 / frozen≥30：信号 408 条，覆盖 35 支。
  - full≥120 / frozen≥10：信号 401 条，覆盖 34 支。
  - full≥120 / frozen≥15：信号 401 条，覆盖 34 支。
  - full≥120 / frozen≥20：信号 401 条，覆盖 34 支。
  - full≥120 / frozen≥30：信号 401 条，覆盖 34 支。
- 推荐门槛（120/30）：**401 条信号、覆盖 34 支**（GLOBAL 33 / AMERICAN 0 / INTERNATIONAL 1）。
- 未覆盖 22 支 → `eip_uncovered.csv`（含 3 支无信号的新基金）。
- 最优策略以 horizon=1 为主（32/34），条件集中在 QQQ/IWM/XLK/SPY 大涨日买科技/成长类基金。
- 抽查验证：`ALLIANZ GLOBAL ARTIFICIAL INTELLIGENCE RT / QQQ_big_up / h=1` 全历史 avg 1.7588%、命中 97.5%，与面板直接手算完全一致。

## 五、产物清单
- 脚本：`02_脚本/新项目_原始ETF/`（make_clean_targets / config_eip / download_eip_funds / clean_eip_funds / build_eip_panel / scan_eip_single / scan_eip_thresholds）。
- 中间结果：`04_结果/新项目_原始ETF/中间结果/`（eip_single_pass / eip_single_baseline_pass / eip_single_best_strategy / eip_threshold_sensitivity / eip_uncovered）。
- 数据（不入 git）：`01_数据/新项目_基金价格/`、`01_数据/新项目_processed/`。

## 六、下一步（Phase 4-6，本轮未做）
- Phase 4 每基金 1-5 条策略选择（多信号合并与冲突规则）。
- Phase 5 m30 新版式 Excel（按 AMERICAN/GLOBAL/INTERNATIONAL 拆分 + 未覆盖单独表）。
- Phase 6 质检、报告与交付包。
