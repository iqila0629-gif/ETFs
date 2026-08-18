# -*- coding: utf-8 -*-
"""Probe TwelveData / EODHD coverage for representative funds."""
import json, time, urllib.request, urllib.parse, pathlib

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
TD, EO = cfg["twelvedata"], cfg["eodhd"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def td_search(q):
    u = f"https://api.twelvedata.com/symbol_search?symbol={urllib.parse.quote(q)}&apikey={TD}"
    try:
        d = json.loads(get(u))
    except Exception as e:
        return [("ERR", str(e))]
    out = []
    for it in (d.get("data") or [])[:5]:
        out.append((it.get("symbol"), it.get("instrument_name"), it.get("exchange"), it.get("instrument_type"), it.get("country")))
    return out

def eo_search(q):
    u = f"https://eodhd.com/api/search/{urllib.parse.quote(q)}?api_token={EO}&fmt=json"
    try:
        d = json.loads(get(u))
    except Exception as e:
        return [("ERR", str(e))]
    return [(x.get("Code"), x.get("Name"), x.get("Type"), x.get("Exchange")) for x in d[:6]]

def eo_fund(isin):
    u = f"https://eodhd.com/api/fundamentals/{isin}?api_token={EO}&fmt=json"
    try:
        t = get(u)
        if t.strip().startswith("["): return t[:120]
        d = json.loads(t)
        if "General" in d:
            g = d["General"]
            return ("OK", g.get("Code"), g.get("Name"), g.get("Type"), g.get("Exchange"))
        return ("NO-GENERAL", t[:120])
    except Exception as e:
        return ("ERR", str(e))

probes = [
    ("ARBROOK G10 AMERICAN EQUITIES", "Arbrook American Equities", "IE00BZ60K206"),
    ("CT MGMT AMERICAN 3U", "CT Lux American", "LU1864949380"),
    ("FRANKLIN TEMPLETON GLOBAL FOCUS", "Franklin Global Focus", ""),
    ("NG MORNINGSTAR GLOBAL GROWTH", "Morningstar Global Growth", ""),
    ("RUSSELL OLD MUTUAL VALUE", "Russell Old Mutual Value", ""),
    ("MONTLAKE QUILTER CHEVIOT INTERNATIONAL", "Quilter Cheviot International", "LU2495477510"),
    ("PICTET GLOBAL MEGATREND I USD", "Pictet Global Megatrend Selection", "LU2518694729"),
    ("FTGF WESTERN ASSET GLOBAL HIGH YIELD", "Western Asset Global High Yield", ""),
    ("NEUBERGER GLOBAL SENIOR FLOATING", "Neuberger Berman Global Senior Floating Rate", ""),
    ("MIV GLOBAL MEDTECH P3 USD", "MIV Global Medtech", ""),
]

for label, q, isin in probes:
    print("#####", label)
    print("  TD search:", json.dumps(td_search(q), ensure_ascii=False)[:400])
    if isin:
        print("  EO fundamentals:", json.dumps(eo_fund(isin), ensure_ascii=False)[:200])
    else:
        print("  EO search:", json.dumps(eo_search(q), ensure_ascii=False)[:300])
    time.sleep(0.3)

# account status
try:
    print("TD account:", get(f"https://api.twelvedata.com/account?apikey={TD}")[:300])
except Exception as e:
    print("TD account ERR", e)