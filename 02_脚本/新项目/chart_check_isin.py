# -*- coding: utf-8 -*-
"""Chart-check the ISIN-derived Yahoo symbols."""
import urllib.request, urllib.parse, json, time, pathlib, csv, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
CACHE = json.loads((BASE / "01_数据" / "eip_isin_yahoo_cache.json").read_text(encoding="utf-8"))
OUT = BASE / "01_数据" / "eip_isin_chart_check.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.4

def chart(sym):
    p1 = int(datetime.datetime(1998, 1, 1).timestamp())
    p2 = int(datetime.datetime(2026, 8, 15).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    ts = res.get("timestamp") or []
    meta = res.get("meta", {})
    return len(ts), ts[0] if ts else None, ts[-1] if ts else None, meta.get("currency")

rows = []
have = 0
for nm, v in CACHE.items():
    if not v:
        continue
    try:
        n, f, l, cur = chart(v["symbol"])
    except Exception:
        n, f, l, cur = 0, None, None, ""
    if n > 0:
        have += 1
    rows.append({"name": nm, "symbol": v["symbol"], "rows": n, "first": f, "last": l, "currency": cur or ""})
    time.sleep(SLEEP)

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "symbol", "rows", "first", "last", "currency"])
    w.writeheader()
    w.writerows(rows)
print("DONE checked:", len(rows), "with data:", have)