# -*- coding: utf-8 -*-
"""Analyze the missing set (no-data + wrong) grouped by fund family."""
import pathlib, csv, re
from collections import Counter

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NO = list(csv.DictReader(open(BASE / "01_数据" / "eip_no_data_final.csv", encoding="utf-8-sig")))
WRONG = list(csv.DictReader(open(BASE / "01_数据" / "eip_wrong.csv", encoding="utf-8-sig")))

def family(name):
    n = name.upper()
    if any(k in n for k in ["TREASURY", "BILLS", "NOTES", "BOND", "5.015%", "3.125%", "4.125%", "3.5%", "3.05%", "5.766%", "3.35%"]):
        return "[债券/票据]"
    if any(k in n for k in ["AUTOCALL", "RECOVERY SAFE", "RECOVERY NOTE", "PHOENIX", "ROCQ"]):
        return "[结构性]"
    if any(k in n for k in ["COM USD", "SHS ", "NPV USD", "CORP COM", "DEPOSITARY"]):
        return "[股票/ADR]"
    toks = re.split(r"\s+", name)
    # fund family = first 1-3 meaningful tokens
    stop = {"THE","OF","AND","INV","INVESTORS","FUND","FUNDS","GLOBAL","SICAV","LUX","SA","PLC","LTD","CO","LTD","MGMT","INVESTMENT"}
    keep = []
    for t in toks:
        tt = t.upper().strip(".,-")
        if tt in stop: continue
        keep.append(tt)
        if len(keep) >= 2: break
    return " ".join(keep[:2])

c = Counter()
for r in NO:
    c[family(r["name"])] += 1
print("== no-data (149) by family ==")
for k, v in c.most_common(40):
    print(f"  {k:28} {v}")
print("\n== wrong (21) by family ==")
cw = Counter(family(r["name"]) for r in WRONG)
for k, v in cw.most_common(25):
    print(f"  {k:28} {v}")