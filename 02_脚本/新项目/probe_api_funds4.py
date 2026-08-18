# -*- coding: utf-8 -*-
import json, urllib.request, pathlib

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
EO = cfg["eodhd"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:150]

tests = [
    ("CT (Lux) American 3U", "LU1864949380.EUFUND"),
    ("Threadneedle Latin American", "GB0002977949.EUFUND"),
    ("Arbrook American Equities", "IE00BZ60K206.EUFUND"),
]
for label, sym in tests:
    u = f"https://eodhd.com/api/eod/{sym}?api_token={EO}&fmt=json&from=2026-07-01"
    st, b = get(u)
    if st == 200 and b.strip().startswith("["):
        d = json.loads(b)
        print(label, sym, "-> OK rows:", len(d), "first:", d[0]["date"], "last:", d[-1]["date"], "close:", d[-1]["close"])
    else:
        print(label, sym, "->", st, b[:120])