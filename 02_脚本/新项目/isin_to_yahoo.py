# -*- coding: utf-8 -*-
"""For FT-matched names, search Yahoo by ISIN to get a Yahoo symbol (cached)."""
import urllib.request, urllib.parse, json, time, pathlib, csv

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
MERGED = BASE / "01_数据" / "eip_merged_candidates.csv"
CACHE = BASE / "01_数据" / "eip_isin_yahoo_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.4

def yahoo_search_isin(isin):
    url = ("https://query1.finance.yahoo.com/v1/finance/search?q=" + isin
           + "&quotesCount=8&newsCount=0")
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            qs = d.get("quotes", [])
            # prefer Fund type, then any
            funds = [q for q in qs if (q.get("typeDisp") or "").lower() == "fund"]
            pool = funds if funds else qs
            if not pool:
                return None
            q = pool[0]
            return {"symbol": q.get("symbol"), "shortname": q.get("shortname"),
                    "type": q.get("typeDisp"), "exch": q.get("exchange")}
        except Exception:
            time.sleep(3 * (a + 1))
    return None

def main():
    rows = list(csv.DictReader(open(MERGED, encoding="utf-8-sig")))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [r for r in rows if r["ft_isin_cur"]]
    found = 0
    for i, r in enumerate(todo, 1):
        nm = r["name"]
        isin_cur = r["ft_isin_cur"]
        isin = isin_cur.split(":")[0]
        if nm not in cache:
            res = yahoo_search_isin(isin)
            cache[nm] = res
            time.sleep(SLEEP)
        if cache.get(nm):
            found += 1
        if i % 20 == 0:
            print(f"[{i}/{len(todo)}] found={found}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print("DONE", len(todo), "found:", found)

if __name__ == "__main__":
    main()