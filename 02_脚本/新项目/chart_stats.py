# -*- coding: utf-8 -*-
import csv, pathlib, datetime
from collections import Counter

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
rows = list(csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_chart_check.csv", encoding="utf-8-sig")))

def to_dt(x):
    try:
        return datetime.datetime.utcfromtimestamp(int(x))
    except Exception:
        return None

print("total:", len(rows))
cat_stat = Counter()
have_stat = Counter()
first_years = []
last_ok_2026 = 0
short_hist = 0
type_counter = Counter()
for r in rows:
    cat = r["category"].split("/")[0]
    cat_stat[cat] += 1
    ok = bool(r["rows_ok"]) and int(r["rows_ok"]) > 0
    have_stat[(cat, "have" if ok else "no")] += 1
    if ok:
        f = to_dt(r["first"]); l = to_dt(r["last"])
        if f: first_years.append(f.year)
        if l and l >= datetime.datetime(2026, 7, 1):
            last_ok_2026 += 1
        if f and f.year >= 2015:
            short_hist += 1
        type_counter[r["best_type"]] += 1

print("\nby category:")
for c in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    print(f"  {c:15} total={cat_stat[c]:3}  have={have_stat[(c,'have')]:3}  no={have_stat[(c,'no')]:3}")

print("\nhave=292 breakdown:")
print("  last date >= 2026-07:", last_ok_2026)
print("  first date >= 2015 (short history):", short_hist)
fy = sorted(first_years)
print("  first-year range:", fy[0], "-", fy[-1], "| median:", fy[len(fy)//2])
print("  best_type:", dict(type_counter))

# rows count distribution
import statistics
nvals = [int(r["rows_ok"]) for r in rows if r["rows_ok"]]
print("  rows median:", statistics.median(nvals), "min:", min(nvals), "max:", max(nvals))