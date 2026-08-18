# -*- coding: utf-8 -*-
"""Audit: fetch Yahoo chart meta for all 304 symbols, score match vs our name / FT name."""
import urllib.request, urllib.parse, json, time, pathlib, csv, re, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
COV = list(csv.DictReader(open(BASE / "01_数据" / "eip_final_coverage.csv", encoding="utf-8-sig")))
META_CACHE = BASE / "01_数据" / "eip_audit_meta.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.4

def chart_meta(sym):
    p2 = int(datetime.datetime(2026, 8, 15).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={p2}&interval=1d")
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            meta = d["chart"]["result"][0].get("meta", {})
            return {"shortName": meta.get("shortName", ""), "longName": meta.get("longName", ""),
                    "currency": meta.get("currency", ""), "type": meta.get("instrumentType", ""),
                    "exch": meta.get("fullExchangeName", "")}
        except Exception:
            time.sleep(3 * (a + 1))
    return {"shortName": "", "longName": "", "currency": "", "type": "", "exch": ""}

meta = json.loads(META_CACHE.read_text(encoding="utf-8")) if META_CACHE.exists() else {}
todo = [r for r in COV if r["status"] == "有数据"]
for i, r in enumerate(todo, 1):
    sym = r["symbol"]
    if sym not in meta:
        meta[sym] = chart_meta(sym)
        time.sleep(SLEEP)
    if i % 30 == 0:
        print(f"[{i}/{len(todo)}] symbols cached: {len(meta)}", flush=True)
        META_CACHE.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
META_CACHE.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
print("DONE cached:", len(meta))