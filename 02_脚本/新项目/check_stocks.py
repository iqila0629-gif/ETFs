# -*- coding: utf-8 -*-
import pathlib, csv
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
R = list(csv.DictReader(open(BASE / "01_数据" / "eip_retry_results.csv", encoding="utf-8-sig")))
for nm in ["DELL INTERNATIONAL LLC USD", "BK OF AMERICA CORP COM USD0.01 USD", "EVOLUTION SHS UNSPONSORED AMERICAN DEPOSITARY RECEIPT REPR 1 SH USD", "UNILEVER SHS SPONSORED AMERICAN DEPOSITARY SHARES REPR 1 SH USD", "AMERICAN BITCOIN CORP NPV USD"]:
    for r in R:
        if r["name"] == nm:
            print(nm[:50])
            print("   query:", r["query"], "| sym:", r["symbol"], "| hit:", r["hit_name"][:50], "| rows:", r["rows"], "| status:", r["status"])