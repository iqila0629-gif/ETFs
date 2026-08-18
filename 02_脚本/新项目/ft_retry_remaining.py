# -*- coding: utf-8 -*-
"""FT retry for remaining 72 funds with 2-tier queries."""
import urllib.request, urllib.parse, re, json, time, pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
REMAIN = list(csv.DictReader(open(BASE / "01_数据" / "eip_remaining_missing.csv", encoding="utf-8-sig")))
CACHE = BASE / "01_数据" / "eip_ft_remaining_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.4

NOISE = {"ACC","DIS","INC","NAV","USD","HKD","EUR","GBP","SGD","AUD","CAD","CHF","SEK","DKK","NOK","ZAR","JPY",
    "ACCUMULATION","DISTRIBUTION","CLASS","CLS","SICAV","SHS","COM","NPV","LUX","LUXEMBOURG","UCITS","PLC","SA","CO",
    "CORP","CORPORATION","INCORPORATED","ADR","REPR","SPONSORED","UNSPONSORED","DEPOSITARY","RECEIPT","RECEIPTS","P.A.",
    "LTD","LIMITED","UNITS","UNIT","HDG","MF","SERIES","OF","THE","AND","FUND","PORTFOLIO","TRUST","ISSUER","A1","A2",
    "A3","B1","B2","B3","C1","C2","D2","D5","I2","L2","M2","P3","Q1","Q2","R2","R3","T2","W2","X2","Y2","Z2","2A2",
    "3D","AT","AM","RT","WT","GT","GTH","B","C","I","A","X","Y","Z","D","E","F","G","H","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","INVESTORS","INVESTOR","MGMT","MANAGEMENT","ASSET","INVESTMENT","INTERNATIONAL","GLOBAL"}
SINGLE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

def clean_tokens(name):
    out = []
    for t in re.split(r"[\s\-/]+", name):
        t = t.strip(".,'\"()")
        if not t: continue
        tu = t.upper()
        if tu in NOISE: continue
        if re.fullmatch(r"\d+(\.\d+)?%?", tu): continue
        if len(tu) == 1 and tu in SINGLE: continue
        if re.fullmatch(r"\d[A-Za-z]+", tu): continue
        out.append(t)
    return out

def ft_search(q, retries=2):
    url = "https://markets.ft.com/data/search?query=" + urllib.parse.quote(q)
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                txt = r.read().decode("utf-8", "ignore")
            rows = []
            for m in re.finditer(r'<a href="/data/funds/tearsheet/summary\?s=([A-Z]{2}\d{10}:[A-Z]{2,4})"[^>]*>(.*?)</a>', txt):
                rows.append({"isin_cur": m.group(1), "name": re.sub(r"<[^>]+>", "", m.group(2)).strip()})
            return rows
        except Exception:
            time.sleep(4 * (a + 1))
    return []

def main():
    funds = [r for r in REMAIN if r["kind"] == "基金"]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    found = 0
    for i, r in enumerate(funds, 1):
        nm = r["name"]
        if nm in cache:
            if cache[nm]: found += 1
            continue
        toks = clean_tokens(nm)
        res = []
        for q in [" ".join(toks[:6]), " ".join(toks[:3]), " ".join(toks[:2])]:
            if not q: continue
            res = ft_search(q)
            if res:
                cache[nm] = res
                found += 1
                break
        if nm not in cache:
            cache[nm] = []
        if i % 12 == 0:
            print(f"[{i}/{len(funds)}] found={found}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(SLEEP)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print("DONE funds:", len(funds), "with FT results:", found)

if __name__ == "__main__":
    main()