# -*- coding: utf-8 -*-
"""Score match quality for the 304 has-data names; classify confirm/suspect/wrong."""
import json, pathlib, csv, re
from collections import Counter

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
COV = list(csv.DictReader(open(BASE / "01_数据" / "eip_final_coverage.csv", encoding="utf-8-sig")))
META = json.loads((BASE / "01_数据" / "eip_audit_meta.json").read_text(encoding="utf-8"))

CURRENCIES = {"USD","HKD","EUR","GBP","SGD","AUD","CAD","CNH","CNY","CHF","SEK","DKK","NOK","ZAR","JPY","NZD","TWD","KRW","INR","RMB"}
NOISE = CURRENCIES | {"ACC","DIS","ACCUMULATION","DISTRIBUTION","INC","CLASS","CLS","SICAV","LUX","LUXEMBOURG",
    "FUND","PORTFOLIO","TRUST","ISSUER","SERIES","PLC","SA","CO","LTD","LIMITED","THE","OF","AND","UCITS",
    "SHS","COM","NPV","CORP","CORPORATION","INCORPORATED","ADR","REPR","SPONSORED","UNSPONSORED","DEPOSITARY",
    "RECEIPT","RECEIPTS","NAV","HDG","MF","UNITS","UNIT","AT","AM","RT","WT","GT","P2","P3","A1","I2","L2","M2",
    "R2","T2","W2","2A2","3D","EP","S14","S1","INVESTORS","INVESTOR","FCP","B","C","I","A","X","Y","Z","D","E",
    "F","G","H","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","CO."}

def toks(s):
    if not s:
        return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip(".,'\"()")}

def theme(s):
    return toks(s) - NOISE

def overlap(a, b):
    ta, tb = theme(a), theme(b)
    if not ta or not tb:
        return 0.0
    return round(len(ta & tb) / min(len(ta), len(tb)), 2)

rows = []
verdicts = Counter()
for r in COV:
    if r["status"] != "有数据":
        continue
    sym = r["symbol"]
    m = META.get(sym, {})
    yahoo_name = (m.get("longName") or m.get("shortName") or "").strip()
    if not yahoo_name or yahoo_name.upper().startswith(sym.split(".")[0][:8]):
        yahoo_name = (m.get("shortName") or "")
    ref = r["ft_name"] if r["source"] == "FT-ISIN->Yahoo" else r["name"]
    sc = overlap(ref, yahoo_name)
    our_cur = next((c for c in CURRENCIES if c in toks(r["name"])), None)
    cur_ok = (not our_cur) or (m.get("currency", "").upper() == our_cur) or (r["source"] == "FT-ISIN->Yahoo" and (r["isin"] or "").split(":")[-1].upper() == m.get("currency", "").upper())
    if not yahoo_name or (not m.get("longName") and not m.get("shortName")):
        verdict = "无名称信息"
    elif sc >= 0.5 and cur_ok:
        verdict = "确认"
    elif sc >= 0.5 and not cur_ok:
        verdict = "存疑-币种不符"
    elif sc >= 0.25:
        verdict = "存疑"
    else:
        verdict = "疑似误配"
    verdicts[verdict] += 1
    rows.append({
        "name": r["name"], "category": r["category"], "source": r["source"], "symbol": sym,
        "isin": r["isin"], "ref_name": ref, "yahoo_name": yahoo_name,
        "overlap": sc, "currency_ok": cur_ok, "yahoo_currency": m.get("currency", ""),
        "yahoo_type": m.get("type", ""), "verdict": verdict,
    })

with open(BASE / "01_数据" / "eip_audit_result.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print("total audited:", len(rows))
print("verdicts:", dict(verdicts))
print("\n-- 疑似误配 --")
for r in [x for x in rows if x["verdict"] == "疑似误配"]:
    print(f"  [{r['source']}] {r['name'][:42]:44} | {r['symbol']:14} | {r['yahoo_name'][:48]}")
print("\n-- 存疑 --")
for r in [x for x in rows if x["verdict"].startswith("存疑")]:
    print(f"  [{r['source']}] {r['name'][:42]:44} | {r['symbol']:14} | {r['yahoo_name'][:48]} | cur={r['yahoo_currency']}")
print("\n-- 无名称信息 --")
for r in [x for x in rows if x["verdict"] == "无名称信息"]:
    print(f"  [{r['source']}] {r['name'][:42]:44} | {r['symbol']:14}")