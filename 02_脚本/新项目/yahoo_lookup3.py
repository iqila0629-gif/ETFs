# -*- coding: utf-8 -*-
"""Yahoo search lookup v3: 4-tier query cascade, keep thematic words, strip security metadata."""
import urllib.request, urllib.parse, json, time, pathlib, re, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES_CSV = BASE / "01_数据" / "eip_fund_names.csv"
CACHE = BASE / "01_数据" / "eip_yahoo_search_cache.json"
BACKUP = BASE / "01_数据" / "eip_yahoo_search_cache_v2_backup.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.35

SEC_META = {  # security-type / share-class metadata to strip anywhere
    "ACC", "DIS", "INC", "NAV", "USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD",
    "CNH", "CNY", "CHF", "SEK", "DKK", "NOK", "ZAR", "JPY", "AUD",
    "ACCUMULATION", "DISTRIBUTION", "CLASS", "CLS", "SICAV", "SHS", "COM", "NPV",
    "LUX", "LUXEMBOURG", "UCITS", "PLC", "SA", "CO", "CORP", "CORPORATION",
    "INCORPORATED", "ADR", "ADRS", "REPR", "REPRESENTING", "REPRESENTS", "SPONSORED",
    "UNSPONSORED", "DEPOSITARY", "RECEIPT", "RECEIPTS", "P.A.", "LTD", "LIMITED",
    "UNITS", "UNIT", "HDG", "MF", "SERIES", "SUPER", "NOTE", "NOTES", "BILL", "BILLS",
    "TREASURY", "TREASURIES", "OF", "THE", "AND", "A1", "A2", "A3", "B1", "B2", "B3",
    "C1", "C2", "D2", "D5", "I2", "L2", "M2", "P3", "Q1", "Q2", "R2", "R3", "T2", "W2",
    "X2", "Y2", "Z2", "2A2", "3D", "AT", "AM", "RT", "WT", "GT", "B", "GTH",
}
# tokens that are usually single-letter share-class suffixes
SINGLE_LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
# stock-like hint tokens
STOCK_HINTS = ("COM", "SHS", "NPV", "ADR", "DEPOSITARY", "CORP", "INC", "LTD", "CORPORATION", "TREASURY", "BILL", "NOTES")

def yahoo_search(q, count=10, retries=2):
    url = ("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q)
           + f"&quotesCount={count}&newsCount=0")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d.get("quotes", [])
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []

def clean_tokens(name):
    toks = re.split(r"[\s\-/]+", name)
    out = []
    for t in toks:
        t = t.strip(".,'\"()")
        if not t:
            continue
        tu = t.upper()
        if tu in SEC_META:
            continue
        if re.fullmatch(r"\d+(\.\d+)?%?", tu):
            continue
        if len(tu) == 1 and tu in SINGLE_LETTERS:
            continue
        if re.fullmatch(r"\d[A-Za-z]+", tu):  # like 2A2, 3D
            continue
        out.append(t)
    return out

def build_queries(name):
    qs = []
    qs.append(name[:90])
    toks = clean_tokens(name)
    if len(toks) >= 3:
        qs.append(" ".join(toks[:8]))
    if len(toks) >= 4:
        qs.append(" ".join(toks[:5]))
    if len(toks) >= 3:
        qs.append(" ".join(toks[:3]))
    # stock-like: try first 2-3 words without metadata
    stock_like = any(t.upper() in STOCK_HINTS for t in re.split(r"\s+", name))
    if stock_like and len(toks) >= 2:
        qs.append(" ".join(toks[:2]))
    return qs

def load_names():
    out = []
    with open(NAMES_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out.append(row)
    return out

def main():
    if CACHE.exists() and not BACKUP.exists():
        BACKUP.write_text(CACHE.read_text(encoding="utf-8"), encoding="utf-8")
    names = load_names()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    total_hits = 0
    for i, row in enumerate(names, 1):
        nm = row["name"]
        qs = build_queries(nm)
        found, q_used = [], None
        for q in qs:
            hits = yahoo_search(q)
            if hits:
                found, q_used = hits, q
                break
        cache[nm] = {
            "queries": qs,
            "query_used": q_used,
            "hits": [{"symbol": h.get("symbol"), "shortname": h.get("shortname"),
                      "longname": h.get("longname"), "exch": h.get("exchange"),
                      "type": h.get("typeDisp")} for h in found[:10]],
        }
        if found:
            total_hits += 1
        if i % 20 == 0:
            print(f"[{i}/{len(names)}] cum_hits={total_hits}", flush=True)
        time.sleep(SLEEP)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE total:", len(names), "with hits:", total_hits)

if __name__ == "__main__":
    main()