"""Scan same-fund / same-theme strategy explanations for regime-conditional contradictions."""

from __future__ import annotations

import sys

import pandas as pd

import config

OUT_DIR = config.V4_OUT / "v4_稳健性分析"


def regime_of(text: str) -> str:
    if any(k in text for k in ["风险偏好收缩", "避险需求上升", "恐慌情绪升温"]):
        return "risk_off"
    if any(k in text for k in ["风险偏好回暖", "资金回流风险资产"]):
        return "risk_on"
    return "other"


def direction_of(text: str) -> str:
    if "价格倾向上涨" in text or "反向产品价格倾向上涨" in text:
        return "up"
    if "价格倾向承压" in text or "反向产品价格倾向承压" in text or "防御资产相对承压" in text:
        return "down"
    return "other"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expl = pd.read_csv(OUT_DIR / "v4_strategy_explanation_v3.csv")
    rows = []
    for _, r in expl.iterrows():
        reg = regime_of(str(r["机制"]))
        d = direction_of(str(r["机制"]))
        rows.append({
            "ticker": r["ticker"],
            "fund_name": r["fund_name"],
            "fund_theme": r["fund_theme"],
            "strategy_no": r["strategy_no"],
            "触发条件": r["触发条件"],
            "regime": reg,
            "direction": d,
            "机制": r["机制"],
        })
    df = pd.DataFrame(rows)

    checks = []
    for group_col in ["ticker", "fund_theme"]:
        for name, g in df.groupby(group_col):
            for reg in ["risk_off", "risk_on"]:
                sub = g[g["regime"] == reg]
                if sub.empty:
                    continue
                ups = sub[sub["direction"] == "up"]
                downs = sub[sub["direction"] == "down"]
                if not ups.empty and not downs.empty:
                    checks.append({
                        "group_type": "基金" if group_col == "ticker" else "主题",
                        "group": name,
                        "regime": reg,
                        "up_count": len(ups),
                        "down_count": len(downs),
                        "up_examples": " | ".join(ups["触发条件"].head(3).tolist()),
                        "down_examples": " | ".join(downs["触发条件"].head(3).tolist()),
                    })
    result = pd.DataFrame(checks)
    result.to_csv(OUT_DIR / "v4_explanation_conflict_check.csv", index=False)
    print("conflict rows:", len(result))
    print(result.to_string(index=False) if len(result) else "no regime-conditional conflicts found")


if __name__ == "__main__":
    main()
