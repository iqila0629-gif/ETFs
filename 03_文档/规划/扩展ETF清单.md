# 扩展 ETF 清单：覆盖剩余基金与提升信号覆盖

> 日期：2026-07-31
> 目的：为剩余未覆盖基金补充 ETF 触发条件，并扩展现有 19 支 ETF 的信号维度

---

## 一、为什么扩展

当前 19 支 ETF 已覆盖 121/129 支基金。剩余 8 支中：

| 基金 | 已观测到的资产方向 |
|------|-------------------|
| GVPIX / GVPSX | 与 TLT 同日相关性 +0.985，国债/利率类 |
| RRPIX / RRPSX | 与 TLT 相关性 -0.98，利率反向类 |
| RTPIX / RTPSX | 与 TLT 相关性 -0.87 ~ -0.91，利率反向类 |
| RDPIX / RDPSX | 与 UUP 相关性 +0.92，美元类 |
| MPIXX / MPSXX | 货币基金，NAV 恒为 1.00，不纳入预测 |

扩展思路：先补齐利率、美元两个方向，再扩板块、商品、风格和国际 ETF，最后用相关性筛查 + 事件研究重新验证。

---

## 二、第一优先：利率 / 债券 ETF

目标：覆盖 GVPIX、RRPIX、RRPSX、RTPIX、RTPSX。

| 代码 | 名称 | 用途 |
|------|------|------|
| IEF | 7-10 年美国国债 | 中期久期基准 |
| SHY | 1-3 年美国国债 | 短久期 |
| BIL | 1-3 月美国国库券 | 现金/极短端 |
| VGSH | 短期美国国债 | 短端补充 |
| MUB | 免税市政债券 | 利率+信用 |
| TMF | 3x 20 年国债 | 放大利率上涨 |
| TMV | -3x 20 年国债 | 做空久期 |
| ZROZ | 25 年+ 国债 STRIPS | 久期最敏感 |
| EDV | 超长期国债 | 久期次敏感 |
| VCLT | 长期公司债 | 久期+信用 |
| VCIT | 中期公司债 | 信用补充 |
| MBB | 房贷抵押债 | 利率+期限结构 |
| SCHP / STIP | TIPS 通胀保护债 | 实际利率 |
| FLRN | 浮动利率债 | 利率上行保护 |
| CLOZ | CLO 证券 | 信用利差补充 |

## 三、第二优先：美元 / 货币 ETF

目标：覆盖 RDPIX、RDPSX。

| 代码 | 名称 | 用途 |
|------|------|------|
| UDN | 反向美元指数 | 美元下跌方向 |
| FXE | 欧元 | 美元兑欧元 |
| FXB | 英镑 | 美元兑英镑 |
| CEW | 新兴市场货币 | 新兴货币方向 |
| DBV | 货币利差（carry） | 套息环境 |

## 四、第三优先：商品 / 黄金 ETF

目标：增强黄金/商品类基金覆盖（现有 GLD、GDX、SLV）。

| 代码 | 名称 | 用途 |
|------|------|------|
| GDXJ | 小型金矿股 | 金矿弹性 |
| IAU | 黄金现货 | 黄金价格 |
| SIL / SLVP | 白银矿业 | 白银弹性 |
| PPLT | 铂金 | 贵金属补充 |
| XME | 金属与矿业 | 基本金属+矿业 |
| COPX | 铜矿 | 铜价 |
| DBB | 基本金属 | 工业金属 |
| DBC | 大宗商品指数 | 商品总体 |
| USO | 原油 | 油价 |
| UNG | 天然气 | 气价 |
| DBA | 农产品 | 农产品 |

## 五、第四优先：板块 / 主题 ETF

目标：补齐当前 19 支 ETF 没有覆盖的行业，提升整体触发率。

| 代码 | 名称 |
|------|------|
| XLB | 材料 |
| XLY | 可选消费 |
| XLP | 必需消费 |
| XLC | 通信服务 |
| XBI / IBB | 生物科技 |
| KBE / KRE | 银行 / 区域银行 |
| XOP / OIH | 油气开采 / 油服 |
| SMH / SOXX | 半导体 |
| IGV | 软件 |
| ARKK | 创新成长 |
| IYR / VNQ / XLRE | 房地产 |
| REM / MORT | 抵押 REITs |

## 六、第五优先：风格 / 小盘 / 国际 ETF

目标：细化已有 SPY/QQQ/IWM/EEM 的维度。

| 分类 | 代码 |
|------|------|
| 小盘补充 | VTWO、IJR、IJH、VB、VXF、AVUV、IWO、IWN |
| 小盘杠杆 | UWM（2x）、TZA（-3x） |
| 风格因子 | MTUM、VLUE、QUAL、USMV、SPLV、RSP |
| 发达市场 | EFA、EWU、EWQ |
| 全球/新兴 | ACWI、VXUS、FXI、EWJ、EWY、EWZ、EWA、INDA、KWEB |

## 七、第六优先：波动率 / 尾部 ETF（可选）

| 代码 | 名称 |
|------|------|
| VXX / VIXY | VIX 期货 |
| UVXY | 2x VIX 期货 |
| SVXY | -1x VIX 期货 |
| VIXM / VXZ | 中期 VIX 期货 |

## 八、第七优先：另类 / 加密（可选）

| 代码 | 名称 |
|------|------|
| BITO | 比特币期货 |
| IBIT | 比特币现货 |
| ETHE | 以太坊信托 |
| GBTC | 比特币信托 |

---

## 九、选取与接入流程

1. 下载：Yahoo Finance 历史日线（参考 `analysis_results/download_and_test_external.py`），或使用 ETF Database 批量获取
2. 计算日回报，与 129 支基金面板按日期对齐
3. 相关性筛查：与至少 1 支基金的同日相关系数绝对值 ≥ 0.6 才保留
4. 优先覆盖剩余基金：
   - GVPIX → IEF / TMF / ZROZ
   - RRPIX / RRPSX → TMF / TMV / ZROZ / EDV
   - RTPIX / RTPSX → IEF / SHY / TMF / TMV
   - RDPIX / RDPSX → UDN / FXE / CEW
5. 加入事件研究：每支新 ETF 跑涨/跌/±1% 条件和幅度分档
6. 样本外验证：walk-forward + 2025-2026 冻结期，方向准确率 ≥45%
7. 保留达标 ETF，输出公司 13 行标准预测 CSV

---

## 十、注意事项

1. 杠杆 ETF（TMF/TMV/UWM/TZA/UVXY 等）有每日复利衰减，只能作为触发信号，不建议作为持仓
2. VIX 期货类 ETF 长期贴水，且与 VIX 指数本身表现不同，需单独验证
3. CLOZ、BITO、IBIT 等成立时间短，无法通过 5 段历史验证，只能作辅助参考
4. 下载前确认 ETF 仍在交易、历史区间和复权方式，避免数据断档
5. 扩展后仍需按基金、按日期去重，避免同一天多条件重复触发

---

## 十一、建议执行顺序

1. 第一批（约 15 支）：IEF、SHY、BIL、TMF、TMV、ZROZ、EDV、MUB、UDN、FXE、CEW、GDXJ、IAU、XME、DBC
2. 第二批（约 15 支）：VGSH、VCLT、VCIT、MBB、SCHP、FLRN、FXB、SIL、COPX、USO、XLB、XLY、XLP、XLC、XBI
3. 第三批（约 20 支）：KBE、KRE、XOP、OIH、SMH、SOXX、IGV、ARKK、IYR、VNQ、XLRE、REM、MTUM、VLUE、QUAL、USMV、RSP、EFA、ACWI、FXI
4. 可选批：EWJ、EWY、EWZ、EWA、INDA、KWEB、VXX、VIXY、UVXY、SVXY、BITO、IBIT

---

## 十二、实际数据获取与验证状态（2026-07-31）

### 数据源实测

| 来源 | 结果 |
|------|------|
| ETFDB | 被 Cloudflare 人机验证拦截，无法直接爬取 |
| Yahoo Finance | 403 拦截，CSV 和 v8 API 均不可用 |
| Stooq | 有 JS 工作量证明验证，验证后仍返回 Access denied |
| Nasdaq API | ✅ 可用，无需登录，30 支 ETF 全部下载成功 |

### 已下载与处理

- 范围：30 支扩展 ETF，2016-08-01 ~ 2026-07-30（Nasdaq 接口约 10 年上限）
- 原始 JSON：`raw_data/etfs_extended/`
- 标准 13 行日回报 CSV：`processed_returns/extended_etf_returns/`
- 合并宽表：`processed_returns/combined_extended_etf_returns.csv`
- 相关性筛查：`analysis_results/event_study/extended_etf_correlation.csv`
- 剩余基金候选条件：`analysis_results/event_study/extended_etf_best_conditions.csv`

### 关键相关性发现

| 基金 | 最强新增 ETF | 同日相关性 | 含义 |
|------|-------------|-----------|------|
| GVPIX | TMF | +0.983 | 长期国债（3x） |
| RRPIX / RRPSX | TMV | +0.977 / +0.984 | 做空长期国债 |
| RTPIX / RTPSX | TMV | +0.857 / +0.899 | 做空长期国债 |
| RDPIX / RDPSX | UDN | 负相关 | 美元多头（与 UUP 正相关 0.92） |

### 验证结果（2025-2026 冻结期）

- 新增通过组合：2 个，均来自 RRPSX：
  - `RRPSX / GDXJ_big_up`：Average -0.3174%
  - `RRPSX / TMF_lt-2`：Average +0.2098%
- 输出：`analysis_results/event_study/sparse_outputs_extended/`
- GVPIX、RDPIX、RDPSX、RRPIX、RTPIX、RTPSX 仍未找到可靠信号

### 第二批扩展（2026-07-31 补充下载）

再下载 27 支 ETF（长期/超长期国债、利率反向、货币、原油、半导体等），合计 **57 支扩展 ETF**：

- 新增：VGLT、GOVZ、SPTL、TLH、IEI、SHV、LTPZ、BND、AGG、VMBS、PFF、TBT、PST、TBF、VGIT、WIP、STIP、EUO、ULE、YCS、YCL、FXA、FXC、XOP、OIH、SMH、SOXX
- 无法获取：DBV、FXCH、CYB（Nasdaq 无数据）

对剩余 5 支空白基金（GVPIX/RDPIX/RDPSX/RTPIX/RTPSX）跑了 4,040 个组合（57 支 ETF × 6 类条件 × 1/2/3/5 日窗口 + 复合条件），新增 8 个冻结期达标信号：

| 基金 | 信号 | Average |
|------|------|---------|
| GVPIX | FXA 单日跌≥1% | -0.6116% |
| GVPIX | WIP 单日跌≥1% | -0.3178% |
| GVPIX | XLC 单日跌>2%（N=2） | -0.2271% |
| RDPIX | FXA 单日跌≥1% | +0.2020% |
| RTPIX | FXA 单日跌≥1% | +0.2311% |
| RTPSX | FXA 单日跌≥1% | +0.2229% |

总覆盖率提升至 **126/129**，仅剩 RDPSX 与 2 支货币基金未覆盖。

验证明细：`analysis_results/event_study/blank_funds_more_etf_validation.csv`
正式输出：`analysis_results/event_study/sparse_outputs_blank_funds/`

### 限制

1. Nasdaq 只有约 10 年历史；当前验证框架（2016-2024 选择期 + 2025-2026 冻结期）已足够，只是无法做 2009 年起的 5 段长周期稳定性验证
2. 杠杆 ETF（TMF/TMV）只作触发信号，不建议持仓
3. 如需完整 1999-2026 历史，建议之后用可访问的付费数据源或人工从券商端导出
