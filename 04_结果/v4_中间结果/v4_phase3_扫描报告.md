# v4 Phase 3 扫描报告：原始 19 支 ETF 三信号穷举

> 日期：2026-08-06
> 数据范围：原始 19 支 ETF + VIX/TNX 外部数据 + 基金自身信号
> 门槛：全历史交易数 `>= 120`、冻结期交易数 `>= 30`；全历史命中率 `> 55%`、冻结期命中率 `>= 55%`、`|Average| >= 0.2%`

## 一、扫描范围

- 三 ETF 组合：`C(19,3) = 969` 组。
- 方向模式：8 种（全涨、全跌、2涨1跌、1涨2跌）。
- 预测窗口：1 / 2 / 3 日。
- 基金：129 支全部参与，不是只扫未覆盖基金。
- 条件-窗口组合：`969 x 8 x 3 = 23,256` 个，每个都评估全部基金。
- 决策规则：expanding walk-forward，禁止未来信息；多日窗口严格要求未来 N 天全部有数据。

## 二、结果

| 信号池 | 信号数 | 覆盖基金 |
|---|---:|---:|
| v4 基线（原始19支，120/30） | 2,674 | 85 |
| 三信号穷举通过 | 39,020 | 93 |
| 合并去重后 | 41,694 | 99 |

三信号新增覆盖 14 支基金：

```text
MGPSX SPPIX SPPSX UFPIX UFPSX UHPIX UHPSX UKPIX UKPSX USPIX USPSX UVPIX UVPSX UXPSX
```

合并后每基金最佳策略中位数：

| 口径 | Average（%） | 交易数 | 命中率 |
|---|---:|---:|---:|
| 全历史 | 0.5645 | 177 | 60.16% |
| 冻结期 | 0.7082 | 41 | 64.52% |

## 三、仍未覆盖

仍未覆盖非货币基金 28 支：

```text
BRPIX BRPSX ETHFX FDPIX FDPSX GVPIX GVPSX RDPIX RDPSX
RRPIX RRPSX RTPIX RTPSX SHPIX SHPSX SNPIX SNPSX SOPIX
SOPSX UCPIX UCPSX UIPIX UIPSX URPIX URPSX UWPIX UWPSX UXPIX
```

## 四、注意

1. 三信号通过量很大（39,020 条），信号之间高度重叠，不能当作独立信号。
2. Phase 4 会从合并信号池中为每支基金选 3-5 条策略，再做冲突规则对比。
3. 剩余 28 支基金需要继续用外部信号、自身信号、高相关 ETF 映射等方法补缺口。
4. 如果未来要新增“特别特别有用”ETF，按 `03_文档/数据说明/v4_新增ETF准入标准.md` 执行。
