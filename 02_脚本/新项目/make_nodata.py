# -*- coding: utf-8 -*-
import csv, pathlib
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
rows = list(csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_chart_check.csv", encoding="utf-8-sig")))
no = [r for r in rows if not (r["rows_ok"] and int(r["rows_ok"]) > 0)]
with open(BASE / "01_数据" / "eip_no_data.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["name", "category", "best_symbol", "note"])
    for r in sorted(no, key=lambda x: x["name"].lower()):
        note = "无Yahoo搜索结果" if not r["best_symbol"] else "候选符号无价格数据"
        w.writerow([r["name"], r["category"], r["best_symbol"], note])
print("no-data count:", len(no))
from collections import Counter
print(Counter(r["category"] for r in no))