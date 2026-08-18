# -*- coding: utf-8 -*-
"""Analyze retry results; compute remaining missing set with candidate ISINs from FT cache."""
import pathlib, csv, json, re

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
RETRY = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_retry_results.csv", encoding="utf-8-sig"))}
NO = list(csv.DictReader(open(BASE / "01_数据" / "eip_no_data_final.csv", encoding="utf-8-sig")))
WRONG = list(csv.DictReader(open(BASE / "01_数据" / "eip_wrong.csv", encoding="utf-8-sig")))
FT = json.loads((BASE / "01_数据" / "eip_ft_search_cache.json").read_text(encoding="utf-8"))

recovered = [r for r in RETRY.values() if r["status"] == "recovered"]
print("recovered:", len(recovered))

# remaining missing = no-data + wrong not recovered
rem = []
for r in NO + WRONG:
    nm = r["name"]
    if nm in RETRY and RETRY[nm]["status"] == "recovered":
        continue
    ft_entries = [x for x in FT.get(nm, {}).get("results", []) if "error" not in x]
    cand_isin = ""
    cand_name = ""
    if ft_entries:
        cand_isin = ft_entries[0]["isin_cur"]
        cand_name = ft_entries[0]["name"]
    n = nm.upper()
    if any(k in n for k in ["TREASURY","BILLS","NOTES","BOND","5.015%","3.125%","4.125%","3.5%","3.05%","5.766%","3.35%","10.00% P.A","7.00% P.A","11.00% P.A"]):
        kind = "债券/票据"
    elif any(k in n for k in ["AUTOCALL","RECOVERY SAFE","RECOVERY NOTE","PHOENIX","ROCQ"]):
        kind = "结构性"
    elif any(k in n for k in ["COM USD","SHS ","NPV USD","CORP COM","DEPOSITARY"]):
        kind = "股票/ADR"
    else:
        kind = "基金"
    rem.append({"name": nm, "category": r["category"], "kind": kind,
                "cand_isin": cand_isin, "cand_ft_name": cand_name, "reason": r.get("reason", "")})

from collections import Counter
print("remaining missing:", len(rem), dict(Counter(x["kind"] for x in rem)))
print("with candidate ISIN:", sum(1 for x in rem if x["cand_isin"]))

with open(BASE / "01_数据" / "eip_remaining_missing.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name","category","kind","cand_isin","cand_ft_name","reason"])
    w.writeheader(); w.writerows(rem)

print("\n-- remaining funds with candidate ISIN (sample) --")
for x in [r for r in rem if r["kind"] == "基金" and r["cand_isin"]][:25]:
    print(f"  {x['cand_isin']:20} {x['name'][:55]}")