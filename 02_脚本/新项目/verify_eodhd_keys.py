# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, pathlib

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
KEYS = [
"6a81f18e855245.20479217",
"6a81ff7dc121b9.29778293",
"6a81fff2c9ec44.71538780",
"6a820029d0e070.17019944",
"6a82005a647034.75218245",
"6a82008d58b3e6.47318721",
"6a8200dbdefef3.78267120",
"6a82010cbf42b0.74577684",
]
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:120]

for k in KEYS:
    u = f"https://eodhd.com/api/eod/AAPL?api_token={k}&fmt=json&from=2026-08-01"
    st, b = get(u)
    if st == 200 and b.strip().startswith("["):
        d = json.loads(b)
        print(k, "-> OK rows:", len(d), "last:", d[-1]["date"])
    else:
        print(k, "->", st, b[:80])