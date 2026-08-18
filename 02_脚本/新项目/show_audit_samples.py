# -*- coding: utf-8 -*-
import pathlib, csv
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
AUD = list(csv.DictReader(open(BASE / "01_数据" / "eip_audit_result.csv", encoding="utf-8-sig")))
print("=== 可用 (确认) 样例 ===")
for r in [x for x in AUD if x["recommendation"] == "可用"][:18]:
    print(f"  {r['name'][:44]:46} | {r['symbol']:14} | {r['yahoo_name'][:52]}")
print("\n=== 待人工核 样例 (币种不符) ===")
for r in [x for x in AUD if x["verdict"] == "存疑-币种不符"][:12]:
    print(f"  {r['name'][:44]:46} | {r['symbol']:14} | {r['yahoo_name'][:44]:46} | {r['yahoo_currency']}")
print("\n=== 剔除 (疑似误配) 全列 ===")
for r in [x for x in AUD if x["recommendation"] == "剔除"]:
    print(f"  {r['name'][:44]:46} | {r['symbol']:14} | {r['yahoo_name'][:46]}")