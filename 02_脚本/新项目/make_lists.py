# -*- coding: utf-8 -*-
import csv, pathlib
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
rows = list(csv.DictReader(open(BASE / "01_数据" / "eip_final_coverage.csv", encoding="utf-8-sig")))
# ISIN list (all names with an ISIN)
isin_rows = [r for r in rows if r["isin"]]
with open(BASE / "01_数据" / "eip_isin_list.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "category", "isin", "ft_name", "yahoo_symbol"])
    w.writeheader()
    for r in sorted(isin_rows, key=lambda x: x["name"].lower()):
        w.writerow({"name": r["name"], "category": r["category"], "isin": r["isin"],
                    "ft_name": r["ft_name"], "yahoo_symbol": r["symbol"] if r["status"] == "有数据" else ""})
# final no-data list
no_rows = [r for r in rows if r["status"] == "无数据"]
with open(BASE / "01_数据" / "eip_no_data_final.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "category", "isin", "reason"])
    w.writeheader()
    for r in sorted(no_rows, key=lambda x: x["name"].lower()):
        reason = r["source"] if r["source"] != "无结果" else "Yahoo+FT均无结果"
        w.writerow({"name": r["name"], "category": r["category"], "isin": r["isin"], "reason": reason})
print("isin list:", len(isin_rows), "| no-data:", len(no_rows))