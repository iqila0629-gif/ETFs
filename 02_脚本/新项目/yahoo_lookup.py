# -*- coding: utf-8 -*-
"""Phase 0 data discovery: Yahoo search lookup for EIP fund names (cached)."""
import urllib.request, urllib.parse, json, time, pathlib, re, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES_CSV = BASE / "01_数据" / "eip_fund_names.csv"
CACHE = BASE / "01_数据" / "eip_yahoo_search_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.35

SHARE_TOKENS = {"ACC", "DIS", "INC", "NAV", "USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD", "CNH", "CNY", "CHF", "SEK", "DKK", "NOK", "ZAR", "JPY", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "ACCUMULATION", "DISTRIBUTION", "CLASS", "SHS", "SICAV"}

def yahoo_search(q, count=10):
    url = ("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q)
           + f"&quotesCount={count}&newsCount=0&enableFuzzyQuery=false")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d.get("quotes", [])

def reduced_query(name):
    toks = [t for t in re.split(r"\s+", name) if t]
    # drop trailing tokens that look like share class / currency / single letters
    while toks and (toks[-1].upper() in SHARE_TOKENS or re.fullmatch(r"\d+[A-Za-z]*", toks[-1])):
        toks.pop()
    # also drop "FUND" / "SICAV" trailing
    while toks and toks[-1].upper() in {"FUND", "SICAV", "TRUST", "PORTFOLIO", "COMPANIES", "COMPANY"} and len(toks) > 3:
        toks.pop()
    return " ".join(toks[:7])

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
    for i, row in enumerate(names, 1):
        nm = row["name"]
        if nm in cache:
            continue
        q1 = nm[:90]
        hits = yahoo_search(q1)
        q_used = q1
        if not hits:
            q2 = reduced_query(nm)
            if q2 and q2 != q1:
                hits = yahoo_search(q2)
                q_used = q2
        cache[nm] = {
            "query_full": q1,
            "query_used": q_used,
            "hits": [{"symbol": h.get("symbol"), "shortname": h.get("shortname"),
                      "longname": h.get("longname"), "exch": h.get("exchange"),
                      "type": h.get("typeDisp")} for h in hits[:10]],
        }
        if i % 25 == 0 or not hits:
            print(f"[{i}/{len(names)}] hits={len(hits)} q={q_used[:50]!r} :: {nm[:45]!r}", flush=True)
        time.sleep(SLEEP)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    total = len(names)
    with_hits = sum(1 for n in names if cache.get(n["name"], {}).get("hits"))
    print(f"DONE {total} names; with hits: {with_hits}")

if __name__ == "__main__":
    main()