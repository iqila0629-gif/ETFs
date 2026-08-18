# -*- coding: utf-8 -*-
"""Analyze Yahoo lookup cache: score best candidate, classify status."""
import json, pathlib, csv, re

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
CACHE = json.loads((BASE / "01_数据" / "eip_yahoo_search_cache.json").read_text(encoding="utf-8"))
NAMES = list(csv.DictReader(open(BASE / "01_数据" / "eip_fund_names.csv", encoding="utf-8-sig")))

STOP = {"ACC","DIS","INC","NAV","USD","HKD","EUR","GBP","SGD","AUD","CAD","CHF","SEK","DKK",
        "NOK","ZAR","JPY","AUD","CLASS","CLS","SICAV","SHS","COM","NPV","LUX","LUXEMBOURG",
        "UCITS","PLC","SA","CO","CORP","CORPORATION","INCORPORATED","ADR","REPR","SPONSORED",
        "UNSPONSORED","DEPOSITARY","RECEIPT","RECEIPTS","LTD","LIMITED","UNITS","UNIT","HDG",
        "MF","SERIES","OF","THE","AND","FUND","PORTFOLIO","TRUST","ISSUER","ETF","ETFS"}

def tokens(s):
    if not s:
        return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip() and t.strip(".,'\"()").upper() not in STOP}

def score(name, cand):
    qt = tokens(name)
    nt = tokens((cand.get("shortname") or "") + " " + (cand.get("longname") or ""))
    if not qt or not nt:
        return 0.0
    inter = len(qt & nt)
    return inter / len(qt) if inter else 0.0

rows = []
status_counts = {"match": 0, "candidate": 0, "none": 0}
for r in NAMES:
    nm = r["name"]
    entry = CACHE.get(nm, {})
    hits = entry.get("hits", [])
    if not hits:
        status = "none"
        best = None
    else:
        scored = [(score(nm, h), h) for h in hits]
        scored.sort(key=lambda x: -x[0])
        best_score, best = scored[0]
        typ = (best.get("type") or "").lower()
        is_clear = best_score >= 0.6
        is_equiv_clear = (typ == "equity" and best_score >= 0.5)
        if is_clear or is_equiv_clear:
            status = "match"
        else:
            status = "candidate"
    status_counts[status] += 1
    rows.append({
        "name": nm, "category": r["category"],
        "status": status,
        "n_hits": len(hits),
        "best_symbol": (best or {}).get("symbol", ""),
        "best_name": ((best or {}).get("shortname") or (best or {}).get("longname") or ""),
        "best_type": (best or {}).get("type", ""),
        "best_exch": (best or {}).get("exchange", ""),
        "best_score": round(best_score, 2) if best else "",
    })

out = BASE / "01_数据" / "eip_yahoo_lookup_result.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print("status:", status_counts)
by_cat = {}
for r in rows:
    by_cat.setdefault(r["category"], {"match": 0, "candidate": 0, "none": 0})
    by_cat[r["category"]][r["status"]] += 1
for cat, d in by_cat.items():
    print(cat, d)

print("\n-- sample MATCH --")
for r in [x for x in rows if x["status"] == "match"][:10]:
    print(f"  {r['name'][:50]:52} -> {r['best_symbol']:12} | {r['best_name'][:45]:47} | {r['best_type']}")
print("\n-- sample CANDIDATE --")
for r in [x for x in rows if x["status"] == "candidate"][:10]:
    print(f"  {r['name'][:50]:52} -> {r['best_symbol']:12} | {r['best_name'][:45]:47} | {r['best_type']}")
print("\n-- sample NONE --")
for r in [x for x in rows if x["status"] == "none"][:12]:
    print(f"  {r['name'][:60]}")