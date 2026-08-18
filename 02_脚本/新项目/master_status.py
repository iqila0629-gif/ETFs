# -*- coding: utf-8 -*-
"""Master status ledger for all 453 names."""
import pathlib, csv
from collections import Counter

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
def load(f):
    return list(csv.DictReader(open(BASE / "01_数据" / f, encoding="utf-8-sig")))

FINAL = {r["name"]: r for r in load("eip_final_coverage.csv")}
AUD = {r["name"]: r for r in load("eip_audit_result.csv")}
RETRY = {r["name"]: r for r in load("eip_retry_results.csv")}
STOCKS = {r["name"]: r for r in load("eip_stock_recovery.csv")}
MANUAL = list(load("eip_manual_download.csv"))

names = list(FINAL.keys())
rows = []
for nm in names:
    if nm in AUD:
        v = AUD[nm]["verdict"]
        if v == "确认": status = "有数据-确认"
        elif v == "疑似误配": status = "有数据-误配待换"
        else: status = "有数据-待人工核"
    elif nm in RETRY and RETRY[nm]["status"] == "recovered":
        status = "有数据-重试找回(待核)"
    elif nm in STOCKS and STOCKS[nm]["status"] == "recovered":
        status = "有数据-股票(确认)"
    else:
        m = next((x for x in MANUAL if x["name"] == nm), None)
        if m and m["kind"] in ("债券/票据", "结构性"):
            status = "无数据-免费源无解"
        else:
            status = "无数据-待人工下载"
    rows.append({"name": nm, "category": FINAL[nm]["category"], "status": status})

with open(BASE / "01_数据" / "eip_master_status.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "category", "status"])
    w.writeheader(); w.writerows(rows)

c = Counter(r["status"] for r in rows)
for k, v in c.most_common():
    print(f"{v:4}  {k}")
print("TOTAL:", len(rows))
print("\nby category:")
cat = Counter((r["category"].split("/")[0], "有数据" if r["status"].startswith("有数据") else "无数据") for r in rows)
for k in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    print(f"  {k:15} 有数据={cat.get((k,'有数据'),0)}  无数据={cat.get((k,'无数据'),0)}")