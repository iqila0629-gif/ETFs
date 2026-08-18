# -*- coding: utf-8 -*-
"""为 FT 核验通过（币种一致）的基金解析正确币种的 Yahoo 符号。
Yahoo ISIN 搜索 -> 候选 -> v7 quote(币种/类型) -> 选 MUTUALFUND 且币种=预期；缓存断点续跑。"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
VERIFY = D / "eip_225_ft_verify.csv"
CACHE = D / "eip_ft225_isin_symbol_cache.json"
OUT = D / "eip_225_repull_list.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(url, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8","ignore"))
        except Exception:
            if a < retries-1: time.sleep(3*(a+1))
            else: return None
def yahoo_search_isin(isin):
    d = get("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(isin) + "&quotesCount=12&newsCount=0")
    return (d or {}).get("quotes", []) or []
def yahoo_quote(sym):
    d = get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(sym))
    q = ((d or {}).get("quoteResponse") or {}).get("result") or []
    return q[0] if q else {}

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    get("https://fc.yahoo.com") if False else None
    try:
        jar.clear() if False else None
    except Exception: pass
    # cookie warm
    try:
        req = urllib.request.Request("https://fc.yahoo.com", headers=UA)
        opener.open(req, timeout=20)
    except Exception: pass
    rows = list(csv.DictReader(open(VERIFY, encoding="utf-8-sig")))
    ok = [r for r in rows if r["verdict"] in ("FT匹配","FT匹配-份额待核","FT匹配-币种一致-名称待核")]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    out = []
    for i, r in enumerate(ok, 1):
        name = r["name"]
        isin_cur = r["best_isin_cur"]
        isin = isin_cur.split(":")[0]
        exp_cur = r["best_c_cur"]
        if isin not in cache:
            cands = yahoo_search_isin(isin)
            scored = []
            for c in cands[:8]:
                sym = c.get("symbol","")
                if not sym: continue
                q = yahoo_quote(sym)
                cur = q.get("currency") or c.get("exchange") or ""
                qtype = q.get("quoteType") or c.get("typeDisp") or ""
                lname = q.get("longName") or q.get("shortName") or ""
                sc = 0
                if qtype == "MUTUALFUND": sc += 2
                if cur == exp_cur: sc += 3
                elif cur: sc += 0.5
                scored.append({"symbol": sym, "currency": cur, "quoteType": qtype, "longname": lname, "score": sc})
                time.sleep(0.25)
            scored.sort(key=lambda x: -x["score"])
            cache[isin] = {"expected_cur": exp_cur, "cands": scored}
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        info = cache.get(isin, {})
        cands = info.get("cands", [])
        best = next((c for c in cands if c["currency"] == exp_cur and c["quoteType"] == "MUTUALFUND"), None)
        if not best:
            best = next((c for c in cands if c["currency"] == exp_cur), None)
        if not best and cands:
            best = cands[0]
        out.append({"name": name, "category": r["category"], "isin_cur": isin_cur,
                    "expected_cur": exp_cur, "symbol": best["symbol"] if best else "",
                    "symbol_currency": best["currency"] if best else "",
                    "symbol_type": best["quoteType"] if best else "",
                    "yahoo_longname": best["longname"] if best else "",
                    "cur_symbol_old": r["cur_symbol"],
                    "n_cands": len(cands),
                    "status": "OK" if best and best["currency"] == exp_cur else ("SYMBOL_FOUND" if best else "NO_SYMBOL")})
        print(f"[{i}/{len(ok)}] {name[:42]:42s} isin={isin} exp={exp_cur} -> {best['symbol'] if best else 'NONE'} ({best['currency'] if best else ''}/{best['quoteType'] if best else ''})", flush=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    import collections
    print("状态:", dict(collections.Counter(r["status"] for r in out)), flush=True)
    print("DONE ->", OUT, flush=True)

if __name__ == "__main__":
    main()