# -*- coding: utf-8 -*-
"""456 结果修正：修正币种/份额类型误判 + Yahoo 名称搜索兜底 + 下载补齐 + 出最终清单。"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar, io, re

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
RESULT = D / "eip_isin456_result.csv"
TARGET = D / "eip_target_isin.csv"
CACHE = D / "eip_isin456_resolve_cache.json"
QFIX = D / "eip_isin456_quote_fix.json"
OUT_DIR = D / "新项目_基金价格_isin"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125", "Accept": "application/json,text/plain,*/*"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def get(url, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 401 and a < tries-1:
                init_session(); time.sleep(2*(a+1)); continue
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

def quote_batch(syms):
    out = {}
    for i in range(0, len(syms), 20):
        chunk = syms[i:i+20]
        try:
            d = json.loads(get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(",".join(chunk)) + "&crumb=" + urllib.parse.quote(crumb)).decode("utf-8","ignore"))
            for q in (d.get("quoteResponse") or {}).get("result", []):
                out[q.get("symbol")] = q
        except Exception:
            pass
        time.sleep(0.25)
    return out

def yahoo_search(q):
    d = json.loads(get("https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q) + "&quotesCount=10&newsCount=0").decode("utf-8","ignore"))
    return d.get("quotes", []) or []

def fetch_chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1=820454400&period2={int(time.time())}&interval=1d&crumb={urllib.parse.quote(crumb)}"
    d = json.loads(get(url).decode("utf-8","ignore"))
    res = d["chart"]["result"][0]
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
    return "\n".join(lines), len(ts), first, last

ETF_KWS = ["ISHARES", "GLOBAL X", "WISDOMTREE"]

def clean_query(name):
    n = re.sub(r"^\d+[、\.\s]+", "", name)
    n = n.replace("\u00a0", " ").replace("\\$", "USD").replace("$", "USD")
    toks = re.split(r"\s+", n.strip().upper())
    drop = {"USD","EUR","HKD","GBP","CHF","AUD","CAD","JPY","SGD","ACC","ACCUMULATION","ACCUMULATING","DIST","DIS","INC","INCOME","NAV","CLASS","FUND"}
    keep = [t for t in toks if t not in drop and len(t) >= 3]
    return " ".join(keep[:8])

def name_sim(cand_name, orig_name):
    a = set(re.split(r"\s+", clean_query(orig_name)))
    b = set(re.split(r"\s+", (cand_name or "").upper().replace("-", " ")))
    if not a: return 0.0
    inter = a & b
    return len(inter) / len(a)

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    init_session()
    rows = list(csv.DictReader(io.open(RESULT, encoding="utf-8-sig")))
    targets = {r["isin"]: r for r in csv.DictReader(io.open(TARGET, encoding="utf-8-sig"))}
    qfix = json.loads(QFIX.read_text(encoding="utf-8")) if QFIX.exists() else {}
    # Phase 1: re-quote all symbols with real currency
    syms = sorted({r["symbol"] for r in rows if r["symbol"]})
    todo = [s for s in syms if s not in qfix]
    print(f"re-quote {len(todo)} symbols...", flush=True)
    for i in range(0, len(todo), 20):
        chunk = todo[i:i+20]
        qmap = quote_batch(chunk)
        for s in chunk:
            qq = qmap.get(s, {})
            qfix[s] = {"currency": qq.get("currency") or "", "quoteType": qq.get("quoteType") or "", "longname": (qq.get("longName") or qq.get("shortName") or "")}
    QFIX.write_text(json.dumps(qfix, ensure_ascii=False), encoding="utf-8")
    print("re-quote done", flush=True)

    # Phase 2: reclassify
    for r in rows:
        isin = r["isin"]; name = r["name"]; sym = r["symbol"]
        q = qfix.get(sym, {})
        cur = (q.get("currency") or "").upper()
        qtype = (q.get("quoteType") or "").upper()
        lname = q.get("longname") or r["longname"] or ""
        nu = name.upper()
        if any(kw in nu for kw in ETF_KWS) or (isin.startswith("US") and (qtype == "ETF" or r["classify"] == "ETF")):
            r["classify"] = "ETF"; r["note"] = "真ETF(名称/美股ETF)"
            continue
        if sym.startswith("0P0000") or qtype in ("MUTUALFUND", "FUND"):
            r["classify"] = "FUND_USD" if cur == "USD" else "NOUSD"
            r["note"] = f"份额线 币种={cur} 类型={qtype}"
            r["currency"], r["quoteType"], r["longname"] = q.get("currency",""), q.get("quoteType",""), lname
            continue
        if qtype == "ETF":
            r["classify"] = "FUND_USD" if cur == "USD" else "NOUSD"
            r["note"] = f"欧洲基金线 币种={cur} 类型=ETF"
            r["currency"], r["quoteType"], r["longname"] = q.get("currency",""), q.get("quoteType",""), lname
            continue
        if qtype == "EQUITY":
            r["classify"] = "NONFUND_STOCK"; r["note"] = "EQUITY"
            continue
        # 无法判定 -> 保持，但 NOUSD/NOSYMBOL/NODATA 留待名称搜索
        r["currency"], r["quoteType"] = q.get("currency",""), q.get("quoteType","")

    # Phase 3: download newly FUND_USD without file
    def have_file(isin):
        return (OUT_DIR / f"{isin}.csv").exists()
    for r in rows:
        if r["classify"] == "FUND_USD" and r["symbol"] and not have_file(r["isin"]):
            try:
                txt, n, f, l = fetch_chart(r["symbol"])
                if n > 0:
                    (OUT_DIR / f"{r['isin']}.csv").write_text(txt + "\n", encoding="utf-8")
                    r["hist_rows"], r["hist_first"], r["hist_last"] = n, f, l
                else:
                    r["classify"] = "NODATA"; r["note"] = "chart空"
            except Exception as e:
                r["classify"] = "NODATA"; r["note"] = str(e)[:100]
            time.sleep(0.3)
    print("phase3 download done", flush=True)

    # Phase 4: Yahoo name-search fallback for funds still lacking USD symbol
    fallback = [r for r in rows if r["classify"] in ("NOSYMBOL", "NODATA", "NOUSD") and not r["isin"].startswith(("XS","US","CA","MH","BM"))]
    print(f"name-search fallback for {len(fallback)} funds...", flush=True)
    ns_cache = {}
    for idx, r in enumerate(fallback, 1):
        isin = r["isin"]
        query = clean_query(r["name"])
        best = None
        try:
            qs = yahoo_search(query)[:10]
            syms = [q.get("symbol") for q in qs if q.get("symbol")]
            qmap = quote_batch(syms) if syms else {}
            scored = []
            for q in qs:
                s = q.get("symbol")
                if not s: continue
                qq = qmap.get(s, {})
                qt = (qq.get("quoteType") or "").upper()
                cu = (qq.get("currency") or "").upper()
                ln = (qq.get("longName") or qq.get("shortName") or q.get("shortname") or "")
                if s.startswith("0P0000") and qt in ("MUTUALFUND", "FUND") and cu == "USD":
                    scored.append((name_sim(ln, r["name"]), s, ln))
            if scored:
                scored.sort(reverse=True)
                best = scored[0]
        except Exception:
            best = None
        ns_cache[isin] = best
        if best and best[0] >= 0.4:
            sym = best[1]
            try:
                txt, n, f, l = fetch_chart(sym)
                if n > 0:
                    (OUT_DIR / f"{isin}.csv").write_text(txt + "\n", encoding="utf-8")
                    r["classify"] = "FUND_USD"; r["symbol"] = sym; r["currency"] = "USD"; r["quoteType"] = "MUTUALFUND"
                    r["longname"] = best[2]; r["hist_rows"], r["hist_first"], r["hist_last"] = n, f, l
                    r["note"] = (r["note"] + "; " if r["note"] else "") + f"Yahoo名称匹配 sim={best[0]:.2f} 待复核"
                else:
                    r["note"] = (r["note"] + "; " if r["note"] else "") + f"名称匹配{sym}但chart空"
            except Exception as e:
                r["note"] = (r["note"] + "; " if r["note"] else "") + f"名称匹配下载失败 {str(e)[:60]}"
        else:
            r["note"] = (r["note"] + "; " if r["note"] else "") + "Yahoo名称搜索无USD份额"
        if idx % 10 == 0:
            print(f"  fallback {idx}/{len(fallback)}", flush=True)
        time.sleep(0.25)

    with io.open(RESULT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # Phase 5: split lists
    def write_list(fn, rows_):
        with io.open(D / fn, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows_)
    write_list("eip_excluded_etf.csv", [r for r in rows if r["classify"] == "ETF"])
    write_list("eip_excluded_nonfund.csv", [r for r in rows if r["classify"] in ("NONFUND_STOCK","NONFUND_BOND","TREASURY","STRUCTURED")])
    write_list("eip_no_usd_share.csv", [r for r in rows if r["classify"] == "NOUSD"])
    write_list("eip_nodata_final.csv", [r for r in rows if r["classify"] in ("NOSYMBOL","NODATA")])
    write_list("eip_fund_ok.csv", [r for r in rows if r["classify"] == "FUND_USD"])
    import collections
    print("最终分类:", dict(collections.Counter(x["classify"] for x in rows)))
    print("下载文件数:", len(list(OUT_DIR.glob("*.csv"))))
    print("DONE")

if __name__ == "__main__":
    main()