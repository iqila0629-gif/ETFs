# -*- coding: utf-8 -*-
import json, urllib.request, urllib.parse, pathlib

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
TD, EO = cfg["twelvedata"], cfg["eodhd"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:
        return 0, str(e)

def td(sym, extra=""):
    u = f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(sym)}&interval=1day&outputsize=3&apikey={TD}{extra}"
    st, b = get(u)
    try:
        d = json.loads(b)
        vals = d.get("values") or []
        return (st, d.get("status"), (d.get("meta") or {}).get("symbol"), len(vals), d.get("code"), d.get("message"))
    except Exception:
        return (st, b[:120])

for label, sym, extra in [
    ("Arbrook 0P0001C875 plain", "0P0001C875", ""),
    ("Arbrook 0P0001C875 .OTC", "0P0001C875.OTC", ""),
    ("Arbrook 0P0001C875 exch=OTC", "0P0001C875", "&exchange=OTC"),
    ("Pictet PBFH exch=FSX", "PBFH", "&exchange=FSX"),
    ("Pictet PBFH.FSX", "PBFH.FSX", ""),
]:
    print(label, "->", json.dumps(td(sym, extra), ensure_ascii=False))

print("--- EODHD variations (body shown) ---")
for label, code in [
    ("Russell IE00BYW8MG91 plain", "IE00BYW8MG91"),
    ("Russell IE00BYW8MG91.USD", "IE00BYW8MG91.USD"),
    ("Russell IE00BYW8MG91.EUFUND", "IE00BYW8MG91.EUFUND"),
]:
    u = f"https://eodhd.com/api/eod/{code}?api_token={EO}&fmt=json&from=2026-07-01"
    print(label, "->", json.dumps(get(u), ensure_ascii=False))