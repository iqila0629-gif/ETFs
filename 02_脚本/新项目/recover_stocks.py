# -*- coding: utf-8 -*-
"""Recover the 4 missing stocks directly from Yahoo chart."""
import urllib.request, urllib.parse, json, time, pathlib, csv, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
STOCKS = [
    ("BK OF AMERICA CORP COM USD0.01 USD", "BAC"),
    ("DELL INTERNATIONAL LLC USD", "DELL"),
    ("EVOLUTION SHS UNSPONSORED AMERICAN DEPOSITARY RECEIPT REPR 1 SH USD", "EVO.ST"),
    ("UNILEVER SHS SPONSORED AMERICAN DEPOSITARY SHARES REPR 1 SH USD", "UL"),
]

def chart(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={int(datetime.datetime(2026,8,15).timestamp())}&interval=1d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    meta = res.get("meta", {})
    ts = res.get("timestamp") or []
    ac = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or []
    return {"rows": len(ts), "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
            "currency": meta.get("currency", ""), "name": meta.get("shortName", ""),
            "adj": ac}

rows = []
for nm, sym in STOCKS:
    try:
        c = chart(sym)
        rows.append({"name": nm, "symbol": sym, "status": "recovered" if c["rows"] else "no-data",
                     "rows": c["rows"], "first": c["first"], "last": c["last"],
                     "currency": c["currency"], "yahoo_name": c["name"], "adj_last": (c["adj"][-1] if c["adj"] else "")})
    except Exception as e:
        rows.append({"name": nm, "symbol": sym, "status": "ERR", "rows": 0, "first": "", "last": "", "currency": "", "yahoo_name": str(e), "adj_last": ""})
    time.sleep(1)

with open(BASE / "01_数据" / "eip_stock_recovery.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
for r in rows:
    print(r["status"], "|", r["symbol"], "|", r["rows"], "rows |", r["yahoo_name"][:45], "|", r["currency"], "| first", r["first"], "-> last", r["last"])