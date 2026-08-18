# -*- coding: utf-8 -*-
"""FT Markets name search for all EIP fund names (cached, resumable)."""
import urllib.request, urllib.parse, re, json, time, pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES_CSV = BASE / "01_数据" / "eip_fund_names.csv"
CACHE = BASE / "01_数据" / "eip_ft_search_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.3

SEC_META = {
    "ACC", "DIS", "INC", "NAV", "USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD",
    "CNH", "CNY", "CHF", "SEK", "DKK", "NOK", "ZAR", "JPY",
    "ACCUMULATION", "DISTRIBUTION", "CLASS", "CLS", "SICAV", "SHS", "COM", "NPV",
    "LUX", "LUXEMBOURG", "UCITS", "PLC", "SA", "CO", "CORP", "CORPORATION",
    "INCORPORATED", "ADR", "ADRS", "REPR", "REPRESENTING", "REPRESENTS", "SPONSORED",
    "UNSPONSORED", "DEPOSITARY", "RECEIPT", "RECEIPTS", "P.A.", "LTD", "LIMITED",
    "UNITS", "UNIT", "HDG", "MF", "SERIES", "SUPER", "NOTE", "NOTES", "BILL", "BILLS",
    "TREASURY", "TREASURIES", "OF", "THE", "AND", "A1", "A2", "A3", "B1", "B2", "B3",
    "C1", "C2", "D2", "D5", "I2", "L2", "M2", "P3", "Q1", "Q2", "R2", "R3", "T2", "W2",
    "X2", "Y2", "Z2", "2A2", "3D", "AT", "AM", "RT", "WT", "GT", "B", "GTH", "FUND",
    "PORTFOLIO", "TRUST", "ISSUER", "SERIES",
}
SINGLE_LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

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
        if re.fullmatch(r"\d[A-Za-z]+", tu):
            continue
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
        except Exception as e:
            if a < retries:
                time.sleep(4 * (a + 1))
            else:
                return [{"error": str(e)}]

def load_names():
    return list(csv.DictReader(open(NAMES_CSV, encoding="utf-8-sig")))

def main():
    names = load_names()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    done = 0
    with_hits = 0
    for i, row in enumerate(names, 1):
        nm = row["name"]
        if nm in cache:
            done += 1
            if cache[nm].get("results") and not cache[nm]["results"][0].get("error"):
                with_hits += 1
            continue
        toks = clean_tokens(nm)
        q = " ".join(toks[:8]) if toks else nm[:60]
        res = ft_search(q)
        cache[nm] = {"query": q, "results": res}
        if res and not res[0].get("error"):
            with_hits += 1
        done += 1
        if done % 15 == 0:
            print(f"[{done}/{len(names)}] hits={with_hits}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(SLEEP)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print("DONE", done, "with_hits:", with_hits)

if __name__ == "__main__":
    main()