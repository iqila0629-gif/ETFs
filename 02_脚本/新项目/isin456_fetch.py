# -*- coding: utf-8 -*-
"""456 支 ISIN 权威抓取：Yahoo 主力 + EODHD 兜底(非全历史即弃)。
分类：FUND_USD / NOUSD / ETF / NONFUND_STOCK / NONFUND_BOND / TREASURY / STRUCTURED / NOSYMBOL / NODATA / CHART_FAIL / EODHD_OK
断点续跑：eip_isin456_resolve_cache.json
"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar, re, io, random

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
TARGET = D / "eip_target_isin.csv"
CACHE = D / "eip_isin456_resolve_cache.json"
OLD_CACHE = D / "eip_ft225_isin_symbol_cache.json"
OLD_CACHE2 = D / "eip_isin_symbol_cache.json"
OUT_DIR = D / "新项目_基金价格_isin"
RESULT = D / "eip_isin456_result.csv"
OUT_DIR.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125", "Accept": "application/json,text/plain,*/*"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
SLEEP = 0.3

def get(url, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 401 and a < tries-1:
                init_session()
                time.sleep(2*(a+1)); continue
            if a < tries-1: time.sleep(2*(a+1))
            else: raise
        except Exception:
            if a < tries-1: time.sleep(2*(a+1))
            else: raise

crumb = ""
def init_session():
    global crumb
    try: get("https://fc.yahoo.com")
    except Exception: pass
    try:
        crumb = get("https://query1.finance.yahoo.com/v1/test/getcrumb").decode("utf-8","ignore").strip()
    except Exception as e:
        print("crumb FAIL", e, flush=True)

def yahoo_search(isin):
    d = json.loads(get("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(isin) + "&quotesCount=12&newsCount=0").decode("utf-8","ignore"))
    return d.get("quotes", []) or []

def yahoo_quote_batch(syms):
    out = {}
    for i in range(0, len(syms), 20):
        chunk = syms[i:i+20]
        try:
            d = json.loads(get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(",".join(chunk)) + "&crumb=" + urllib.parse.quote(crumb)).decode("utf-8","ignore"))
            for q in (d.get("quoteResponse") or {}).get("result", []):
                out[q.get("symbol")] = q
        except Exception:
            pass
        time.sleep(SLEEP)
    return out

def fetch_chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1=820454400&period2={int(time.time())}&interval=1d&crumb={urllib.parse.quote(crumb)}"
    d = json.loads(get(url).decode("utf-8","ignore"))
    res = d["chart"]["result"][0]
    meta = res.get("meta", {})
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    adj = (res["indicators"].get("adjclose", [{}])[0] or {}).get("adjclose", [])
    lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
    for i in range(len(ts)):
        def val(arr):
            return f"{arr[i]:.6f}" if i < len(arr) and arr[i] is not None else ""
        lines.append(f"{time.strftime('%Y-%m-%d', time.gmtime(ts[i]))},{val(q.get('open',[]))},{val(q.get('high',[]))},{val(q.get('low',[]))},{val(q.get('close',[]))},{val(q.get('volume',[]))},{val(adj)}")
    first = time.strftime("%Y-%m-%d", time.gmtime(ts[0])) if ts else ""
    last = time.strftime("%Y-%m-%d", time.gmtime(ts[-1])) if ts else ""
    return "\n".join(lines), len(ts), first, last, meta.get("currency",""), meta.get("instrumentType","")

def eodhd_probe(isin, keys):
    random.shuffle(keys)
    for k in keys[:4]:
        u = f"https://eodhd.com/api/eod/{isin}.EUFUND?api_token={k}&fmt=json&order=d"
        try:
            b = get(u).decode("utf-8","replace")
            d = json.loads(b)
            if isinstance(d, dict) and (d.get("error") or "limit" in str(d).lower() or "daily" in str(d).lower()):
                continue
            rows = d if isinstance(d, list) else []
            if not rows:
                continue
            first = rows[0].get("date",""); last = rows[-1].get("date","")
            return len(rows), first, last
        except Exception:
            continue
    return 0, "", ""

def pre_classify(r):
    isin, name = r["isin"], r["name"].upper()
    if isin.startswith("XS"):
        return "STRUCTURED", "XS 结构性产品/债券"
    if isin[:2] in ("CA", "MH", "BM"):
        return "NONFUND_STOCK", "CA/MH/BM 上市公司股票"
    if isin == "CH1300646267":
        return "NONFUND_STOCK", "瑞士注册上市公司(BUNGE)"
    if isin.startswith("US"):
        if "TREASURY" in name or isin.startswith(("US9127", "US9128")):
            return "TREASURY", "美国国债/国库券"
        if (" NOTES " in name or name.endswith(" NOTES") or " LLC" in name or "%" in name):
            return "NONFUND_BOND", "公司债/票据"
        if " COM" in name or "SHS" in name or "DEPOSITARY" in name or " ADR" in name or " CORP" in name or " INC " in name:
            return "NONFUND_STOCK", "美股/ADR"
        if "GLOBAL X" in name:
            return "ETF", "GLOBAL X 美国上市ETF"
        return None
    return None

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    init_session()
    rows = list(csv.DictReader(io.open(TARGET, encoding="utf-8-sig")))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    old1 = json.loads(OLD_CACHE.read_text(encoding="utf-8")) if OLD_CACHE.exists() else {}
    old2 = json.loads(OLD_CACHE2.read_text(encoding="utf-8")) if OLD_CACHE2.exists() else {}
    keys = json.loads((D / "api_keys.json").read_text(encoding="utf-8"))["eodhd_list"]
    results = []
    for idx, r in enumerate(rows, 1):
        isin = r["isin"]
        name = r["name"]
        rec = {"isin": isin, "name": name, "sheet": r["sheet"], "classify": "", "symbol": "", "currency": "", "quoteType": "", "longname": "", "hist_rows": "", "hist_first": "", "hist_last": "", "note": ""}
        pc = pre_classify(r)
        if pc:
            rec["classify"], rec["note"] = pc
            results.append(rec); continue
        info = cache.get(isin)
        if not info:
            cands = []
            try:
                if isin in old1 and old1[isin].get("cands"):
                    cands = old1[isin]["cands"]
                else:
                    qs = yahoo_search(isin)[:8]
                    syms = [q.get("symbol") for q in qs if q.get("symbol")]
                    qmap = yahoo_quote_batch(syms) if syms else {}
                    for q in qs:
                        s = q.get("symbol")
                        if not s: continue
                        qq = qmap.get(s, {})
                        cands.append({"symbol": s, "currency": qq.get("currency") or "", "quoteType": qq.get("quoteType") or "", "longname": (qq.get("longName") or qq.get("shortName") or q.get("shortname") or "")})
                    if not cands and isin in old2 and old2[isin].get("symbol"):
                        s = old2[isin]["symbol"]
                        qmap = yahoo_quote_batch([s])
                        qq = qmap.get(s, {})
                        if qq:
                            cands.append({"symbol": s, "currency": qq.get("currency") or "", "quoteType": qq.get("quoteType") or "", "longname": qq.get("longName") or qq.get("shortName") or ""})
            except Exception:
                cands = []
            info = {"cands": cands}
            cache[isin] = info
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            time.sleep(SLEEP)
        cands = info.get("cands") or []
        def score(c):
            sc = 0
            t = (c.get("quoteType") or "").upper()
            cur = (c.get("currency") or "").upper()
            if t == "MUTUALFUND": sc += 4
            if cur == "USD": sc += 2
            if t == "ETF": sc += 1
            return sc
        cands_sorted = sorted(cands, key=score, reverse=True)
        best = cands_sorted[0] if cands_sorted else {}
        sym = ""
        if not best:
            rec["classify"] = "NOSYMBOL"
            rec["note"] = "Yahoo 无搜索结果"
        else:
            t = (best.get("quoteType") or "").upper()
            cur = (best.get("currency") or "").upper()
            sym = best.get("symbol","")
            rec["symbol"], rec["currency"], rec["quoteType"], rec["longname"] = sym, best.get("currency",""), best.get("quoteType",""), best.get("longname","")
            mfusd = next((c for c in cands if (c.get("quoteType") or "").upper()=="MUTUALFUND" and (c.get("currency") or "").upper()=="USD"), None)
            if mfusd and t != "MUTUALFUND":
                best = mfusd; t="MUTUALFUND"; cur="USD"; sym=best["symbol"]
                rec["symbol"], rec["currency"], rec["quoteType"], rec["longname"] = sym, best.get("currency",""), best.get("quoteType",""), best.get("longname","")
            if t == "MUTUALFUND" and cur == "USD":
                rec["classify"] = "FUND_USD"
            elif t == "MUTUALFUND":
                rec["classify"] = "NOUSD"
                rec["note"] = f"Yahoo 仅 {cur} 份额(非USD)"
            elif t == "ETF":
                rec["classify"] = "ETF"
            else:
                rec["classify"] = "NONFUND_STOCK"
                rec["note"] = f"quoteType={t}"
        if rec["classify"] == "FUND_USD" and rec["symbol"]:
            try:
                txt, n, f, l, cur, it = fetch_chart(rec["symbol"])
                if n > 0:
                    fn = OUT_DIR / f"{isin}.csv"
                    fn.write_text(txt + "\n", encoding="utf-8")
                    rec["hist_rows"], rec["hist_first"], rec["hist_last"] = n, f, l
                else:
                    rec["classify"] = "NODATA"
                    rec["note"] = "Yahoo chart 空"
            except Exception as e:
                rec["classify"] = "CHART_FAIL"
                rec["note"] = str(e)[:120]
        print(f"[{idx}/{len(rows)}] {rec['classify']:14s} {isin} {sym if sym else '':14s} {name[:36]}", flush=True)
        results.append(rec)
    eod_done = 0
    for rec in results:
        if rec["classify"] not in ("NOSYMBOL", "NOUSD", "CHART_FAIL", "NODATA"):
            continue
        if rec["isin"].startswith(("XS", "US", "CA", "MH", "BM")):
            continue
        n, f, l = eodhd_probe(rec["isin"], keys)
        eod_done += 1
        if n and f:
            ok = f <= "2022-01-01"
            rec["note"] = (rec["note"] + "; ") + f"EODHD {n}行 {f}->{l} " + ("(全历史可接受)" if ok else "(非全历史-弃)")
            if rec["classify"] in ("NOSYMBOL","CHART_FAIL","NODATA") and ok:
                rec["classify"] = "EODHD_OK"
        else:
            rec["note"] = (rec["note"] + "; ") + "EODHD 无数据"
        time.sleep(0.2)
        if eod_done % 10 == 0:
            print(f"  eodhd probed {eod_done}", flush=True)
    with io.open(RESULT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    import collections
    print("分类统计:", dict(collections.Counter(x["classify"] for x in results)))
    print("DONE ->", RESULT)

if __name__ == "__main__":
    main()