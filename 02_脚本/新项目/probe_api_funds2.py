# -*- coding: utf-8 -*-
"""Probe 2: pull actual history for TD/EODHD symbols, check credit usage."""
import json, urllib.request, urllib.parse, pathlib

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
TD, EO = cfg["twelvedata"], cfg["eodhd"]

def get(url, show_headers=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read().decode("utf-8", "replace")
        hdrs = dict(r.headers) if show_headers else None
        return body, hdrs

def td_series(sym, out=5):
    u = f"https://api.twelvedata.com/time_series?symbol={urllib.parse.quote(sym)}&interval=1day&outputsize={out}&apikey={TD}"
    try:
        b, h = get(u, show_headers=True)
        d = json.loads(b)
        vals = d.get("values") or []
        meta = d.get("meta") or {}
        n = len(vals)
        first = vals[-1].get("datetime") if vals else None
        last = vals[0].get("datetime") if vals else None
        return (d.get("status"), meta.get("symbol"), n, first, last, d.get("code"), d.get("message"), (h.get("X-RateLimit-Remaining") or ""))
    except Exception as e:
        return ("EXC", str(e))

def eo_eod(code):
    u = f"https://eodhd.com/api/eod/{code}?api_token={EO}&fmt=json&from=2026-07-01"
    try:
        b, _ = get(u)
        if b.strip().startswith("["):
            d = json.loads(b)
            return ("OK", len(d), d[0].get("date"), d[-1].get("date"))
        return ("ERR", b[:160])
    except Exception as e:
        return ("EXC", str(e))

for label, sym in [
    ("TD Arbrook A1 USD Acc 0P0001C875", "0P0001C875"),
    ("TD NG Morningstar Global Growth A USD 0P00017YVR", "0P00017YVR"),
    ("TD Neuberger Global Senior Float I USD Acc 0P0000YVJG", "0P0000YVJG"),
    ("TD Pictet Megatrend PBFH(FSX)", "PBFH"),
    ("TD MIV Medtech P3 USD 0P0000ZSTV", "0P0000ZSTV"),
]:
    print(label, "->", json.dumps(td_series(sym), ensure_ascii=False))

print("--- EODHD eod tests (2 calls) ---")
print("EO Russell Old Mutual Value IE00BYW8MG91 ->", json.dumps(eo_eod("IE00BYW8MG91"), ensure_ascii=False))
print("EO Western Asset Global HY A US$ Acc IE00B1BXHP82 ->", json.dumps(eo_eod("IE00B1BXHP82"), ensure_ascii=False))