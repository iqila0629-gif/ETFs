# -*- coding: utf-8 -*-
"""Final coverage: union of FT-ISIN->Yahoo and Yahoo-name sources."""
import json, pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES = list(csv.DictReader(open(BASE / "01_数据" / "eip_fund_names.csv", encoding="utf-8-sig")))
MERGED = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_merged_candidates.csv", encoding="utf-8-sig"))}
YCHK = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_chart_check.csv", encoding="utf-8-sig"))}
ISIN_SYM = json.loads((BASE / "01_数据" / "eip_isin_yahoo_cache.json").read_text(encoding="utf-8"))
ISIN_CHK = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_isin_chart_check.csv", encoding="utf-8-sig"))}

rows = []
for r in NAMES:
    nm = r["name"]
    m = MERGED.get(nm, {})
    isin = (m.get("ft_isin_cur") or "").split(":")[0]
    ic = ISIN_CHK.get(nm)
    isin_has = bool(ic and ic["rows"] and int(ic["rows"]) > 0)
    isin_sym = (ISIN_SYM.get(nm) or {}).get("symbol", "") if isin else ""
    yc = YCHK.get(nm)
    y_has = bool(yc and yc["rows_ok"] and int(yc["rows_ok"]) > 0)
    y_sym = (m.get("yahoo_name_sym") or "") if not isin_has else ""
    if isin_has:
        status, source, sym = "有数据", "FT-ISIN->Yahoo", isin_sym
    elif y_has:
        status, source, sym = "有数据", "Yahoo按名称", y_sym
    else:
        status, source, sym = "无数据", ("有ISIN无Yahoo数据" if isin else "无结果"), ""
    rows.append({
        "name": nm, "category": r["category"],
        "status": status, "source": source, "symbol": sym,
        "isin": isin, "ft_name": m.get("ft_best_name", ""),
        "yahoo_name_sym": m.get("yahoo_name_sym", ""),
        "isin_sym": isin_sym,
    })

with open(BASE / "01_数据" / "eip_final_coverage.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

from collections import Counter
print("total:", len(rows))
print("status:", dict(Counter(r["status"] for r in rows)))
print("source:", dict(Counter(r["source"] for r in rows)))
bycat = {}
for r in rows:
    bycat.setdefault(r["category"].split("/")[0], Counter())
    bycat[r["category"].split("/")[0]][r["status"]] += 1
for c in ["AMERICAN", "GLOBAL", "INTERNATIONAL"]:
    print(c, dict(bycat.get(c, {})))
# gain over previous Yahoo-only
prev_no = [r["name"] for r in rows if not (YCHK.get(r["name"], {}).get("rows_ok") and int(YCHK.get(r["name"], {}).get("rows_ok", 0) or 0) > 0)]
gain = [r["name"] for r in rows if r["status"] == "有数据" and r["name"] in prev_no]
print("previously no-data count:", len(prev_no), "| now recovered via FT path:", len(gain))