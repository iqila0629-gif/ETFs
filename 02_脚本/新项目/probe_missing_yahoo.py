# -*- coding: utf-8 -*-
"""Probe Yahoo clean-query retry for a sample of missing names."""
import urllib.request, urllib.parse, json, time, re

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def yahoo_search(q, count=12):
    url = "https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q) + f"&quotesCount={count}&newsCount=0"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8")).get("quotes", [])

# (fund name, clean query)
samples = [
    ("BK OF AMERICA CORP COM USD0.01 USD", "Bank of America"),
    ("EVOLUTION SHS UNSPONSORED AMERICAN DEPOSITARY RECEIPT REPR 1 SH USD", "Evolution"),
    ("UNILEVER SHS SPONSORED AMERICAN DEPOSITARY SHARES REPR 1 SH USD", "Unilever ADR"),
    ("BROWN ADVISORY GLOBAL LEADERS", "Brown Advisory"),
    ("CAUSEWAY BNP PARIBAS EMERGING MARKETS", "Causeway Emerging Markets"),
    ("NEXT GEN GLOBAL LONG SHORT FUND", "Next Generation Global"),
    ("ARBROOK G10 AMERICAN EQUITIES A1 USD ACC USD", "Arbrook"),
    ("BARING INTL (IRE) GLOBAL EMG MARK USD", "Baring Global Emerging Markets"),
    ("IIF EQUITY INCOME FUND", "IIF Equity Income"),
    ("PICTET MEGATREND SELECTION I EUR", "Pictet Megatrend"),
    ("FRANKLIN TEMPLETON LATIN AMERICA A ACC USD", "Franklin Latin America"),
    ("JPMORGAN IF GLOBAL UNCONSTRAINED EQUITY", "JPMorgan Global Unconstrained"),
]
for nm, q in samples:
    try:
        qs = yahoo_search(q)
        print(f"\nQ: {q!r}  (for {nm[:40]}) -> {len(qs)}")
        for x in qs[:6]:
            print("   ", x.get("symbol"), "|", (x.get("shortname") or "")[:50], "|", x.get("typeDisp"))
    except Exception as e:
        print(f"\nQ: {q!r} ERR {e}")
    time.sleep(1)