# -*- coding: utf-8 -*-
"""Probe: Yahoo ISIN search multi-candidates; Yahoo chart by ISIN-as-symbol."""
import urllib.request, urllib.parse, json, time

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ISINS = {
    "LU0107464264": "abrdn SICAV I - Future Global Equity Fund A Acc USD",
    "LU0260065031": "AB SICAV I - International Technology Portfolio Class S USD",
    "LU1747735568": "AB FCP I - Global High Yield Portfolio WT USD Inc",
    "LU0348825331": "Allianz China Equity A USD",
}

def search(q):
    url = "https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q) + "&quotesCount=12&newsCount=0"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8")).get("quotes", [])

def chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1=0&period2=1786627800&interval=1d"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    res = d["chart"]["result"][0]
    meta = res.get("meta", {})
    ts = res.get("timestamp") or []
    return len(ts), meta.get("shortName"), meta.get("currency"), meta.get("instrumentType")

for isin, want in ISINS.items():
    print("\n==== ISIN", isin, "| want:", want[:55])
    try:
        qs = search(isin)
        print("quotes:", len(qs))
        for q in qs:
            nm = (q.get("longname") or q.get("shortname") or "")
            print("   ", q.get("symbol"), "|", (q.get("shortname") or "")[:45], "|", (q.get("longname") or "")[:45], "|", q.get("exchange"), "|", q.get("typeDisp"))
    except Exception as e:
        print("search ERR:", e)
    time.sleep(1)
    # try chart with ISIN as symbol
    try:
        n, sn, cur, typ = chart(isin)
        print("chart-as-ISIN:", n, "rows |", sn, "|", cur, "|", typ)
    except Exception as e:
        print("chart-as-ISIN ERR:", e)
    time.sleep(1)