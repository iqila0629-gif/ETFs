# -*- coding: utf-8 -*-
import csv, pathlib
p = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_api_download_log.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
for r in rows:
    if r["status"] in ("OK", "NOT_FOUND"):
        print(f"{r['status']:9} | {r['name'][:58]:58} | {r['symbol']:26} | rows={r['rows']} | {r['first']}..{r['last']} | {r['note'][:36]}")
print("---")
from collections import Counter
print(dict(Counter(r["status"] for r in rows)))