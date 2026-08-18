# -*- coding: utf-8 -*-
"""Final classification from audit: confirmed / needs-review / drop, by category & source."""
import pathlib, csv
from collections import Counter

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
AUD = list(csv.DictReader(open(BASE / "01_数据" / "eip_audit_result.csv", encoding="utf-8-sig")))

def rec(verdict):
    if verdict == "确认": return "可用"
    if verdict == "疑似误配": return "剔除"
    return "待人工核"

for r in AUD:
    r["recommendation"] = rec(r["verdict"])

with open(BASE / "01_数据" / "eip_audit_result.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(AUD[0].keys()))
    w.writeheader(); w.writerows(AUD)

for name, filt in [("eip_confirmed.csv", lambda r: r["recommendation"] == "可用"),
                   ("eip_needs_review.csv", lambda r: r["recommendation"] == "待人工核"),
                   ("eip_wrong.csv", lambda r: r["recommendation"] == "剔除")]:
    rows = [r for r in AUD if filt(r)]
    with open(BASE / "01_数据" / name, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(AUD[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(name, len(rows))

print("\nverdict counts:", dict(Counter(r["verdict"] for r in AUD)))
print("recommendation:", dict(Counter(r["recommendation"] for r in AUD)))
print("\nby source (recommendation):")
for src in sorted(set(r["source"] for r in AUD)):
    print(" ", src, dict(Counter(r["recommendation"] for r in AUD if r["source"] == src)))
print("\nby category (recommendation):")
for cat in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    print(" ", cat, dict(Counter(r["recommendation"] for r in AUD if r["category"].split("/")[0] == cat)))