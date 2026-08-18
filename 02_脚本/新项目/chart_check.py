# -*- coding: utf-8 -*-
"""Validate chart availability for best candidate symbols."""
import urllib.request, urllib.parse, json, time, pathlib, csv, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
RESULT = BASE / "01_数据" / "eip_yahoo_lookup_result.csv"
OUT = BASE / "01_数据" / "eip_yahoo_chart_check.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
    return len(ts), ts[0] if ts else None, ts[-1] if ts else None, meta.get("currency"), meta.get("shortName")

rows = list(csv.DictReader(open(RESULT, encoding="utf-8-sig")))
out_rows = []
have = 0
no = 0
err = 0
for i, r in enumerate(rows, 1):
    sym = r["best_symbol"]
    status = r["status"]
    rec = dict(r)
    if not sym:
        rec.update(rows_ok="", first="", last="", currency="", chart_name="")
        out_rows.append(rec)
        no += 1
        continue
    try:
        n, f, l, cur, cn = chart(sym)
        rec.update(rows_ok=n, first=f, last=l, currency=cur or "", chart_name=cn or "")
        if n > 0:
            have += 1
        else:
            no += 1
    except Exception as e:
        rec.update(rows_ok=0, first="", last="", currency="", chart_name="ERR")
        err += 1
        no += 1
    out_rows.append(rec)
    if i % 30 == 0:
        print(f"[{i}/{len(rows)}] have={have} no={no} err={err}", flush=True)
    time.sleep(SLEEP)

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)
print("DONE have:", have, "no:", no, "err:", err)