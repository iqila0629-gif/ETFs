# -*- coding: utf-8 -*-
"""Phase 0: parse EIP name lists -> normalized, deduped name CSV."""
import re, unicodedata, pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\新数据")
OUTDIR = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\01_数据")
OUTDIR.mkdir(exist_ok=True)

FILES = {
    "AMERICAN": BASE / "EIP AMERICAN.txt",
    "GLOBAL": BASE / "EIP GLOBAL.txt",
    "INTERNATIONAL": BASE / "EIP INTERNATIONAL.txt",
}

def normalize(s: str) -> str:
    s = s.replace("\u3000", " ")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"^\s*\d+\s*[、.．]\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

rows = []
for cat, p in FILES.items():
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            rows.append({"category": cat, "raw_name": ln, "name": normalize(ln)})

seen = {}
for r in rows:
    key = r["name"].lower()
    if key in seen:
        if r["category"] not in seen[key]["category"]:
            seen[key]["category"] += "/" + r["category"]
    else:
        seen[key] = r

all_names = list(seen.values())
out = OUTDIR / "eip_fund_names.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "raw_name", "category"])
    w.writeheader()
    for r in sorted(all_names, key=lambda x: x["name"].lower()):
        w.writerow({"name": r["name"], "raw_name": r["raw_name"], "category": r["category"]})

print("total raw lines:", len(rows))
print("unique names:", len(all_names))
from collections import Counter
print("by category:", dict(Counter(r["category"] for r in all_names)))
for r in sorted(all_names, key=lambda x: x["name"].lower())[:12]:
    print(repr(r["name"]), "|", r["category"])