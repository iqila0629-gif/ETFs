# -*- coding: utf-8 -*-
import csv, pathlib, re
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
rows = list(csv.DictReader(open(BASE / "01_数据" / "eip_final_coverage.csv", encoding="utf-8-sig")))
no = [r for r in rows if r["status"] == "无数据"]
def kind(r):
    n = r["name"].upper()
    if any(k in n for k in ["TREASURY", "BILL", "NOTES", "NOTE", "BOND", "5.015%", "3.125%", "4.125%", "3.5%", "3.05%", "5.766%", "3.35%"]):
        return "债券/票据"
    if any(k in n for k in ["AUTOCALL", "RECOVERY SAFE", "RECOVERY NOTE", "PHOENIX", "STRUCTURED"]):
        return "结构性产品"
    if any(k in n for k in ["COM USD", "SHS ", "NPV ", "CORP", "CORPORATION", "INC ", "ADR"]):
        return "股票/ADR"
    return "基金"
from collections import Counter
print("no-data total:", len(no))
print("by kind:", dict(Counter(kind(r) for r in no)))
print("by category:", dict(Counter(r["category"].split('/')[0] for r in no)))
print("\n-- 有ISIN但Yahoo无数据 (4) --")
for r in [r for r in rows if r["source"] == "有ISIN无Yahoo数据"]:
    print("  ", r["name"][:60], "|", r["isin"], "|", r["ft_name"][:50])
print("\n-- 无数据中的股票/ADR (应可再查) --")
for r in [r for r in no if kind(r) == "股票/ADR"]:
    print("  ", r["name"][:65])