# -*- coding: utf-8 -*-
"""复核 repull 列表符号的真实币种/类型（带 crumb），筛选 USD MUTUALFUND/FUND，生成最终重拉清单。"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar, collections

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(url, retries=3, as_json=True):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                b = r.read().decode("utf-8","ignore")
                return json.loads(b) if as_json else b
        except Exception:
            if a < retries-1: time.sleep(3*(a+1))
            else: return None
# crumb (plain text)
for _ in range(2):
    try:
        req = urllib.request.Request("https://fc.yahoo.com", headers=UA); opener.open(req, timeout=20)
    except Exception: pass
crumb = ""
for _ in range(3):
    try:
        cr = get("https://query1.finance.yahoo.com/v1/test/getcrumb", as_json=False)
        if cr:
            crumb = cr.strip(); break
    except Exception: pass
print("crumb:", crumb, flush=True)

rows = list(csv.DictReader(open(D/"eip_225_repull_list.csv", encoding="utf-8-sig")))
CACHE = D / "eip_ft225_symbol_quote_cache.json"
cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
cache = {k: v for k, v in cache.items() if v and v.get("currency")}
out = []
for i, r in enumerate(rows, 1):
    sym = r["symbol"]
    exp = r["expected_cur"]
    if not sym:
        out.append({**r, "real_cur": "", "real_type": "", "usable": "NO_SYMBOL"}); continue
    if sym not in cache:
        d = get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(sym) + "&crumb=" + urllib.parse.quote(crumb))
        q = ((d or {}).get("quoteResponse") or {}).get("result") or []
        cache[sym] = q[0] if q else {}
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.2)
    q = cache.get(sym, {})
    cur = q.get("currency","")
    qtype = q.get("quoteType","")
    lname = q.get("longName") or q.get("shortName") or ""
    usable = bool(sym) and cur == exp and qtype in ("MUTUALFUND","FUND","")
    out.append({**r, "real_cur": cur, "real_type": qtype, "yahoo_longname2": lname, "usable": "OK" if usable else ("CUR_MISMATCH" if sym else "NO_SYMBOL")})
    print(f"[{i}/{len(rows)}] {r['name'][:42]:42s} {sym:22s} cur={cur:>4} type={qtype:10s} usable={usable}", flush=True)
with open(D/"eip_225_repull_final.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader(); w.writerows(out)
print("usable:", dict(collections.Counter(r["usable"] for r in out)), flush=True)