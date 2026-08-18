"""Build a rule-based economic explanation table for delivered m30 strategies (v2 richer)."""

from __future__ import annotations

import re
import sys

import pandas as pd

import config
from build_v4_m30_newformat_sample import condition_label

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
NAMES_CSV = config.ROOT / "04_结果" / "最新成果" / "中间文档" / "通用" / "文件" / "基金名称映射.csv"

ETF_LABEL = {
    "SPY": "标普500", "QQQ": "科技成长", "IWM": "小盘", "TLT": "长期国债",
    "TIP": "通胀保护国债", "EEM": "新兴市场", "LQD": "投资级信用债", "HYG": "高收益债",
    "UUP": "美元", "SLV": "白银", "JNK": "高收益债", "GLD": "黄金", "GDX": "金矿股",
    "XLV": "医疗", "XLU": "公用事业", "XLE": "能源", "XLF": "金融", "XLK": "科技",
    "FXY": "日元", "XLC": "通信服务",
}

EXT_LABEL = {
    "VIX_Close": "VIX水平", "VIX_Chg%": "VIX当日变化", "VIX_5dChg": "VIX近5日变化",
    "VIX_20dVol": "VIX近20日波动", "TNX_Yield": "10年美债收益率", "TNX_ChgBp": "10年美债收益率变动",
    "CreditSpread": "信用利差", "JNKSpread": "高收益利差", "StkBonCorr": "股债相关度",
    "USDGoldRatio": "美元/黄金比", "SectRotation": "科技/金融轮动", "VIX_TNX_Ratio": "VIX/收益率比",
    "YldCurveProxy": "收益率曲线代理",
}

SECTOR_THEME = [
    ("Biotechnology", "生物科技"), ("Banks", "银行金融"), ("Materials", "原材料"),
    ("Consumer Staples", "必需消费"), ("Consumer Discretionary", "可选消费"),
    ("Energy", "能源"), ("Financials", "金融"), ("Financial", "金融"), ("Healthcare", "医疗"),
    ("Health", "医疗"), ("Technology", "科技"), ("Telecommunications", "通信"),
    ("Telecom", "通信"), ("Communication Services", "通信"), ("Utilities", "公用事业"),
    ("Real Estate", "房地产"), ("Gold", "贵金属"), ("Precious Metals", "贵金属"),
    ("Semiconductor", "半导体"), ("Internet", "互联网"), ("Natural Resources", "自然资源"),
    ("Bitcoin", "比特币"), ("High Yield", "高收益"), ("Convertible", "可转债"),
    ("Pharmaceuticals", "医药"), ("Industrials", "工业"), ("Oil & Gas", "能源"),
    ("Oil & Gas Equipment", "能源设备"), ("Government Plus", "国债"), ("Rising Rates", "利率机会"),
]

GEO_THEME = [("China", "中国"), ("Japan", "日本"), ("Europe", "欧洲"), ("Latin America", "拉美"),
             ("International", "国际"), ("Emerging Markets", "新兴市场")]
STYLE_THEME = [
    ("Small-Cap", "小盘"), ("Small", "小盘"), ("Mid-Cap", "中盘"), ("Large-Cap", "大盘"),
    ("Value", "价值"), ("Growth", "成长"), ("Bull", "大盘多头"), ("Bear", "反向"), ("Short", "反向"),
    ("Dow 30", "大盘"), ("NASDAQ-100", "纳指100"),
]


def fund_theme(name: str) -> str:
    low = re.sub(r"\s+", " ", name.lower())
    for kw, label in SECTOR_THEME:
        if kw.lower() in low:
            return label
    for kw, label in GEO_THEME:
        if kw.lower() in low:
            return label
    for kw, label in STYLE_THEME:
        if kw.lower() in low:
            return label
    return "主题基金"


def parse_parts(condition: str) -> list[str]:
    if condition.startswith("combo_"):
        return condition[len("combo_"):].split("__")
    tokens = condition.split("_")
    if len(tokens) in (4, 6) and tokens[0] in ETF_LABEL and tokens[2] in ETF_LABEL and set(tokens[1::2]) <= {"up", "down"}:
        return [f"{tokens[i]}_{tokens[i + 1]}" for i in range(0, len(tokens), 2)]
    return [condition]


def parse_single(part: str) -> tuple[str | None, str | None]:
    if part.startswith("self_"):
        suffix = part[len("self_"):]
        if suffix.endswith("up"):
            return "self", suffix
        if suffix.endswith("down"):
            return "self", suffix
        return "self", suffix
    if part.startswith("ext_"):
        rest = part[len("ext_"):]
        for safe, col in [
            ("vix_close", "VIX_Close"), ("vix_chg", "VIX_Chg%"), ("tnx_yield", "TNX_Yield"),
            ("tnx_chgbp", "TNX_ChgBp"), ("vix_5dchg", "VIX_5dChg"), ("vix_20dvol", "VIX_20dVol"),
            ("credit_spread", "CreditSpread"), ("jnk_spread", "JNKSpread"),
            ("stk_bon_corr", "StkBonCorr"), ("usd_gold_ratio", "USDGoldRatio"),
            ("sect_rotation", "SectRotation"), ("vix_tnx_ratio", "VIX_TNX_Ratio"),
            ("yld_curve_proxy", "YldCurveProxy"),
        ]:
            prefix = f"{safe}_"
            if rest.startswith(prefix):
                op = rest[len(prefix):]
                return "ext", f"{col}|{op}"
        return "ext", rest
    tokens = part.split("_")
    if len(tokens) >= 2 and tokens[0] in ETF_LABEL:
        return "etf", f"{tokens[0]}|{'_'.join(tokens[1:])}"
    return None, None


def roles_for(part: str) -> list[str]:
    kind, payload = parse_single(part)
    roles: list[str] = []
    if kind == "self":
        if payload.endswith("up"):
            roles.append("self_up")
        elif payload.endswith("down"):
            roles.append("self_down")
        if payload == "3down":
            roles.append("streak3_down")
        if payload == "5down":
            roles.append("streak5_down")
        if payload == "3up":
            roles.append("streak3_up")
        if payload == "5up":
            roles.append("streak5_up")
        return roles
    if kind == "etf":
        etf, suffix = payload.split("|")
        up = suffix in {"up", "big_up", "gt2"} or suffix.startswith("bin_")
        label = f"{etf}_{suffix}"
        risk_on = {("SPY", True), ("QQQ", True), ("IWM", True), ("HYG", True), ("JNK", True), ("EEM", True)}
        safe = {("TLT", True), ("GLD", True), ("SLV", True), ("GDX", True), ("FXY", True), ("UUP", True), ("XLU", True), ("XLV", True), ("TIP", True)}
        credit = {("HYG", True), ("JNK", True), ("LQD", True)}
        if (etf, up) in risk_on:
            roles.append("risk_on_up")
        if (etf, not up) in risk_on:
            roles.append("risk_off_down")
        if (etf, up) in safe:
            roles.append("safe_up")
        if (etf, not up) in safe:
            roles.append("safe_down")
        if (etf, up) in credit:
            roles.append("credit_up")
        if (etf, not up) in credit:
            roles.append("credit_down")
        if etf in {"GLD", "SLV", "GDX"}:
            roles.append("gold_up" if up else "gold_down")
        if etf == "UUP":
            roles.append("usd_up" if up else "usd_down")
        if etf == "XLE":
            roles.append("energy_up" if up else "energy_down")
        if etf in {"TLT", "TIP", "FXY"}:
            roles.append("safe_up" if up else "safe_down")
        if etf == "XLK":
            roles.append("sect_growth" if up else "sect_value")
        if etf == "XLF":
            roles.append("sect_value" if up else "sect_growth")
        if etf in {"XLU", "XLV"}:
            roles.append("defensive_up" if up else "defensive_down")
        return roles
    if kind == "ext":
        col, op = payload.split("|")
        up = op in {"up", "ge25", "ge10", "ge20", "ge0_5", "ge1"} or (op.startswith("ge") and not op.startswith("le"))
        if col == "VIX_Chg%" or col == "VIX_5dChg" or col == "VIX_20dVol" or col == "VIX_Close" or col == "VIX_TNX_Ratio":
            roles.append("vix_up" if up else "vix_down")
        if col == "TNX_Yield" or col == "TNX_ChgBp":
            roles.append("rates_up" if up else "rates_down")
        if col in {"CreditSpread", "JNKSpread"}:
            roles.append("credit_down" if up else "credit_up")  # spread down = credit improving
        if col == "YldCurveProxy":
            roles.append("rates_down" if up else "rates_up")
        if col == "USDGoldRatio":
            roles.append("usd_up" if up else "usd_down")
        if col == "SectRotation":
            roles.append("sect_growth" if up else "sect_value")
        if col == "StkBonCorr":
            roles.append("corr_up" if up else "corr_down")
        return roles
    return roles


def mechanism_text(parts: list[str], theme: str) -> str:
    roles: list[str] = []
    for p in parts:
        roles += roles_for(p)

    priority = [
        ("risk_off_down", "风险偏好收缩，资金撤离高风险资产"),
        ("vix_up", "恐慌/波动率上升，避险情绪占优"),
        ("credit_down", "信用利差走阔，信用风险上升"),
        ("safe_up", "避险/利率敏感资产走强（黄金、日元、国债等）"),
        ("gold_up", "贵金属走强，避险与抗通胀需求上升"),
        ("defensive_up", "防御性板块走强，资金寻求低波动"),
        ("risk_on_up", "风险偏好回暖，资金回流权益与信用资产"),
        ("vix_down", "恐慌/波动率回落，市场趋于平静"),
        ("credit_up", "信用环境偏宽松，资金愿意承担信用风险"),
        ("rates_down", "利率下行预期，利好长久期与利率敏感资产"),
        ("rates_up", "利率上行预期，压制长久期资产"),
        ("usd_down", "美元走弱，利好贵金属与新兴市场"),
        ("usd_up", "美元走强，压制贵金属与新兴市场"),
        ("sect_growth", "板块轮动偏向成长/科技"),
        ("sect_value", "板块轮动偏向价值/金融"),
        ("energy_up", "能源板块走强，反映通胀与周期预期"),
        ("energy_down", "能源板块走弱，通胀与周期预期降温"),
        ("defensive_down", "防御性板块走弱，资金风险偏好上升"),
        ("safe_down", "避险资产走弱"),
        ("self_up", "基金自身走强后存在动量延续或高位回落风险"),
        ("self_down", "基金自身下跌/急跌后存在超跌反弹动量"),
        ("streak3_down", "连续3日下跌后超跌反弹概率上升"),
        ("streak5_down", "连续5日下跌后超跌反弹概率上升"),
        ("streak3_up", "连续3日上涨后惯性延续或回调风险并存"),
        ("streak5_up", "连续5日上涨后回调风险上升"),
    ]

    narratives: list[str] = []
    for role, text in priority:
        if role in roles:
            narratives.append(text)

    if "risk_on_up" in roles and "risk_off_down" in roles:
        narratives = [n for n in narratives if n not in (
            "风险偏好回暖，资金回流权益与信用资产",
            "风险偏好收缩，资金撤离高风险资产",
        )]
        narratives.insert(0, "风险偏好与防御信号并存，市场分歧加大")
    if "safe_up" in roles and "safe_down" in roles:
        narratives = [n for n in narratives if n not in (
            "避险/利率敏感资产走强（黄金、日元、国债等）",
            "避险资产走弱",
        )]
        narratives.insert(0, "避险资产表现分化")
    if "defensive_up" in roles and "defensive_down" in roles:
        narratives = [n for n in narratives if n not in (
            "防御性板块走强，资金寻求低波动",
            "防御性板块走弱，资金风险偏好上升",
        )]
        narratives.insert(0, "防御性板块表现分化")

    if not narratives:
        narratives.append("多因子状态组合，反映特定市场环境")
    narratives = narratives[:4]
    cond_text = "，".join(part_text(p) for p in parts)
    return cond_text, "；".join(narratives) + "。"
def part_text(part: str) -> str:
    kind, payload = parse_single(part)
    if kind == "self":
        labels = {
            "up": "自身上涨", "down": "自身下跌", "big_up": "自身大涨(>=2%)",
            "big_down": "自身大跌(<=-2%)", "3up": "自身连续3日上涨",
            "3down": "自身连续3日下跌", "5up": "自身连续5日上涨", "5down": "自身连续5日下跌",
        }
        return labels.get(payload, part)
    if kind == "etf":
        etf, suffix = payload.split("|")
        label = ETF_LABEL.get(etf, etf)
        suffix_text = {
            "up": "上涨", "down": "下跌", "big_up": "大涨(>=1%)", "big_down": "大跌(<=-1%)",
            "gt2": "涨幅>2%", "lt-2": "跌幅<-2%",
        }.get(suffix, suffix.replace("_", "-"))
        return f"{label}{suffix_text}"
    if kind == "ext":
        col, op = payload.split("|")
        label = EXT_LABEL.get(col, col)
        op_text = {
            "up": "上升", "down": "下降", "ge25": ">=25", "le15": "<=15",
            "ge10": ">=10", "le-10": "<=-10", "ge20": ">=20", "le-20": "<=-20",
            "ge0_5": ">=0.5", "le-0_5": "<=-0.5", "ge1": ">=1", "le-1": "<=-1",
        }.get(op, op)
        return f"{label}{op_text}"
    return part


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv", keep_default_na=False)
    names = pd.read_csv(NAMES_CSV)
    name_map = dict(zip(names["ticker"], names["name"]))
    rows = []
    for r in mapping.itertuples(index=False):
        ticker = str(r.ticker)
        condition = str(r.condition)
        parts = parse_parts(condition)
        name = name_map.get(ticker, ticker)
        theme = fund_theme(name)
        cond_text, mech_text = mechanism_text(parts, theme)
        rows.append({
            "ticker": ticker,
            "fund_name": name,
            "fund_theme": theme,
            "strategy_no": int(r.strategy_no),
            "触发条件": condition_label(condition, int(r.horizon)),
            "条件解释": cond_text,
            "机制": mech_text,
        })
    pd.DataFrame(rows).to_csv(OUT_DIR / "v4_strategy_explanation_v3.csv", index=False)
    print("saved explanation rows:", len(rows))


if __name__ == "__main__":
    main()








