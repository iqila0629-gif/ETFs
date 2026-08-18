# -*- coding: utf-8 -*-
"""Improved Yahoo search lookup: aggressive noise-stripped queries."""
import urllib.request, urllib.parse, json, time, pathlib, re, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES_CSV = BASE / "01_数据" / "eip_fund_names.csv"
CACHE = BASE / "01_数据" / "eip_yahoo_search_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.35

NOISE = {
    "ACC", "DIS", "INC", "NAV", "USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD",
    "CNH", "CNY", "CHF", "SEK", "DKK", "NOK", "ZAR", "JPY", "AUD",
    "ACCUMULATION", "DISTRIBUTION", "CLASS", "CLS", "SICAV", "SHS", "COM", "NPV",
    "LUX", "LUXEMBOURG", "UCITS", "PLC", "SA", "AG", "CO", "CORP", "CORPORATION",
    "INCORPORATED", "ADR", "ADRS", "REPR", "REPRESENTING", "REPRESENTS", "SPONSORED",
    "UNSPONSORED", "DEPOSITARY", "RECEIPT", "RECEIPTS", "P.A.", "%", "FUND", "PORTFOLIO",
    "TRUST", "ISSUER", "WORLDWIDE", "MANAGEMENT", "MGMT", "INTERNATIONAL", "GLOBAL",
    "EQUITY", "EQUITIES", "OPPORTUNITIES", "OPPS", "STRATEGIES", "STRATEGIC", "INCOME",
    "GROWTH", "VALUE", "DIVIDEND", "YIELD", "CAPITAL", "SMALL", "MID", "LARGE", "BLEND",
    "SUSTAINABLE", "SUSTAINABILITY", "RESPONSIBLE", "ENHANCED", "SELECT", "SELECTION",
    "DEVELOPED", "EMERGING", "MARKETS", "MARKET", "BOND", "BONDS", "FIXED", "HIGH",
    "LOW", "RISK", "MANAGED", "ALLOCATION", "ASSET", "ASSETS", "MULTI", "MULTI-ASSET",
    "COMPANIES", "COMPANY", "A.I.", "LTD", "LIMITED", "ETF", "ETFS", "SERIES",
}
# do NOT strip these (they are often the distinctive core)
KEEP_HINTS = ("AMERICAN", "LATIN", "CHINA", "JAPAN", "ASIA", "PACIFIC", "US", "GOLD",
              "SILVER", "TECHNOLOGY", "HEALTH", "ENERGY", "CYBER", "ARTIFICIAL", "REAL",
              "ESTATE", "DRAGONS", "FRONTIER", "INDIA", "KOREA", "TAIWAN", "GERMANY",
              "EUROPE", "EUROPEAN", "UK", "BRAZIL", "MEXICO", "RUSSIA", "AFRICA", "A.I.")

def yahoo_search(q, count=10):
    url = ("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q)
           + f"&quotesCount={count}&newsCount=0")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("quotes", [])

def clean_tokens(name):
    toks = re.split(r"[\s\-/]+", name)
    out = []
    for t in toks:
        t = t.strip(".,'")
        if not t:
            continue
        tu = t.upper()
        if tu in NOISE:
            continue
        if re.fullmatch(r"\d+(\.\d+)?%?", tu):
            continue
        if re.fullmatch(r"[A-Z]\d?", tu) and len(tu) == 1:  # single letters like share class
            continue
        out.append(t)
    return out

def build_queries(name):
    toks = clean_tokens(name)
    qs = []
    if len(toks) >= 3:
        qs.append(" ".join(toks[:8]))
    if len(toks) >= 4:
        qs.append(" ".join(toks[:5]))
    if len(toks) >= 3:
        qs.append(" ".join(toks[:3]))
    return qs

def load_names():
    out = []
    with open(NAMES_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out.append(row)
    return out

def main():
    names = load_names()
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    total_hits = 0
    for i, row in enumerate(names, 1):
        nm = row["name"]
        entry = cache.get(nm, {"hits": []})
        qs = build_queries(nm)
        found = []
        q_used = None
        for q in qs:
            try:
                hits = yahoo_search(q)
            except Exception as e:
                print("ERR", nm[:30], e, flush=True)
                time.sleep(2)
                hits = []
            if hits:
                found = hits
                q_used = q
                break
            time.sleep(SLEEP)
        entry["queries"] = qs
        entry["query_used"] = q_used
        entry["hits"] = [{"symbol": h.get("symbol"), "shortname": h.get("shortname"),
                          "longname": h.get("longname"), "exch": h.get("exchange"),
                          "type": h.get("typeDisp")} for h in found[:10]]
        cache[nm] = entry
        if found:
            total_hits += 1
        if i % 20 == 0:
            print(f"[{i}/{len(names)}] cum_hits={total_hits}", flush=True)
        time.sleep(SLEEP)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE total names:", len(names), "with hits:", total_hits)

if __name__ == "__main__":
    main()