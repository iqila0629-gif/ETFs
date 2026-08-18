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


SAFE_THEMES = {"贵金属", "公用事业", "必需消费", "国债", "利率机会", "医疗", "医药"}


def product_profile(name: str, theme: str) -> str:
    low = name.lower()
    if "ultrashort" in low or "ultra short" in low:
        product = "反向杠杆产品（约-2倍）"
    elif "short" in low or "bear" in low:
        product = "反向产品"
    elif "ultra" in low:
        product = "杠杆产品（约2倍）"
    elif "bull" in low:
        product = "多头产品"
    else:
        product = "主题产品"
    return f"{theme}类{product}"


def condition_meaning(roles: list[str]) -> list[str]:
    order = [
        ("risk_off_down", "风险偏好收缩，资金撤离高风险资产"),
        ("vix_up", "恐慌情绪升温"),
        ("credit_down", "信用风险上升，高风险资产承压"),
        ("safe_up", "避险与利率敏感资产走强"),
        ("gold_up", "避险与抗通胀需求上升"),
        ("defensive_up", "资金转向防御性板块"),
        ("rates_down", "利率下行预期升温"),
        ("risk_on_up", "风险偏好回暖，资金回流权益与信用资产"),
        ("vix_down", "恐慌情绪回落"),
        ("credit_up", "信用环境偏宽松"),
        ("rates_up", "利率上行预期升温"),
        ("usd_down", "美元走弱"),
        ("usd_up", "美元走强"),
        ("sect_growth", "板块轮动偏向成长/科技"),
        ("sect_value", "板块轮动偏向价值/金融"),
        ("energy_up", "能源板块走强，通胀与周期预期升温"),
        ("energy_down", "能源板块走弱，通胀与周期预期降温"),
        ("defensive_down", "防御性板块走弱"),
        ("safe_down", "避险资产走弱"),
        ("self_down", "基金自身下跌/急跌"),
        ("self_up", "基金自身走强"),
    ]
    out = []
    for role, text in order:
        if role in roles:
            out.append(text)
        if len(out) >= 2:
            break
    return out or ["多因子条件同时满足"]


def market_impact(roles: list[str]) -> str:
    risk_off = any(r in roles for r in ["risk_off_down", "vix_up", "credit_down", "safe_up", "gold_up", "defensive_up", "rates_down"])
    risk_on = any(r in roles for r in ["risk_on_up", "vix_down", "credit_up", "defensive_down", "safe_down", "rates_up"])
    if risk_off and risk_on:
        impact = "市场风险偏好与防御信号并存，资金分流加剧"
    elif risk_off:
        impact = "资金转向避险与防御资产，风险资产承压"
    elif risk_on:
        impact = "资金回流风险资产，避险资产相对走弱"
    else:
        impact = "市场维持原有风险偏好格局"
    if "usd_down" in roles:
        impact += "，美元走弱利好贵金属与新兴市场"
    if "usd_up" in roles:
        impact += "，美元走强压制贵金属与新兴市场"
    if "sect_growth" in roles:
        impact += "，成长/科技板块相对占优"
    if "sect_value" in roles:
        impact += "，价值/金融板块相对占优"
    if "self_down" in roles:
        impact += "，超跌后存在均值回归动力"
    return impact


def conclusion_text(roles: list[str], theme: str, name: str) -> str:
    low = name.lower()
    inverse = any(k in low for k in ["short", "bear"])
    safe_theme = theme in SAFE_THEMES
    risk_off = any(r in roles for r in ["risk_off_down", "vix_up", "credit_down", "safe_up", "gold_up", "defensive_up", "rates_down"])
    risk_on = any(r in roles for r in ["risk_on_up", "vix_down", "credit_up", "defensive_down", "safe_down", "rates_up"])
    if inverse:
        if risk_off and safe_theme:
            concl = "避险需求上升时贵金属/防御资产走强，反向产品价格倾向承压"
        elif risk_off:
            concl = "风险偏好收缩时高风险资产承压，反向产品价格倾向上涨"
        elif risk_on and safe_theme:
            concl = "风险偏好回暖时防御资产相对走弱，反向产品价格倾向反弹"
        elif risk_on:
            concl = "风险偏好回暖时风险资产走强，反向产品价格倾向承压"
        else:
            concl = "条件触发后反向产品方向取决于标的资产相对强弱"
    else:
        if risk_off and safe_theme:
            concl = "避险需求上升时该基金作为防御/避险资产，价格倾向上涨"
        elif risk_off:
            concl = "风险冲击日该类高Beta/杠杆基金往往超跌，次日存在均值回归（超跌反弹）倾向"
        elif risk_on and safe_theme:
            concl = "风险偏好回暖日防御资产相对落后/超跌，次日存在均值回归回补倾向"
        elif risk_on:
            concl = "风险偏好回暖时该基金价格倾向上涨"
        else:
            concl = "条件触发后该基金价格方向取决于市场状态"
    if "self_down" in roles:
        concl = "基金自身急跌后存在超跌反弹动量" + ("，" + concl if inverse or safe_theme or risk_off or risk_on else "")
    return concl


def mechanism_text(parts: list[str], theme: str, name: str) -> tuple[str, str]:
    roles: list[str] = []
    for p in parts:
        roles += roles_for(p)
    meanings = condition_meaning(roles)
    impact = market_impact(roles)
    profile = product_profile(name, theme)
    concl = conclusion_text(roles, theme, name)
    cond_text = "，".join(part_text(p) for p in parts)
    mech = f"{'；'.join(meanings)}。{impact}。该基金为{profile}，{concl}。"
    return cond_text, mech
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
        cond_text, mech_text = mechanism_text(parts, theme, name)
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










