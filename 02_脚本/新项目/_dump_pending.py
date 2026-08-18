# -*- coding: utf-8 -*-
import csv, pathlib
p = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\01_数据\eip_api_download_log.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
pend = [r for r in rows if r["status"] == "PENDING"]
print("PENDING count:", len(pend))
for r in pend:
    print(f"{r['name'][:56]:56} | {r['note']}")