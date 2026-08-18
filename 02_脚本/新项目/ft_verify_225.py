# -*- coding: utf-8 -*-
"""225 支待复核基金的 FT 身份核验：
1) FT 搜索（多查询词变体）找 ISIN:CUR + FT 官方名（含份额/币种）
2) 对最佳候选抓 FT 历史页（1 个月，HTTP+cookie）确认基金存在且有数据
3) 按 币种/份额/名称家族 打分，输出核验表 eip_225_ft_verify.csv
"""
import urllib.request, urllib.parse, re, json, time, pathlib, csv, sys, http.cookiejar, collections

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
QUERY_CACHE = D / "eip_ft225_query_cache.json"
HIST_CACHE = D / "eip_ft225_hist_cache.json"
OUT = D / "eip_225_ft_verify.csv"

CUR = {"USD","HKD","EUR","GBP","SGD","AUD","CAD","CHF","SEK","DKK","NOK","ZAR","JPY","CNY","CNH","NZD","MXN","PLN","RUB","INR","TWD","KRW"}
META = {"ACC","ACCUMULATION","DIS","DIST","DISTRIBUTION","INC","INCOME","MDIS","CAP","CAPITAL","NAV","HDG","HGD","HEDGED","SICAV","UCITS","FUND","FUNDS","PORTFOLIO","TRUST","CLASS","CLS","SERIES","SHS","COM","NPV","LTD","LIMITED","CORP","CORPORATION","PLC","SA","CO","OF","THE","AND","A1","A2","A3","B1","B2","B3","C1","C2","D2","D5","I2","L2","M2","P3","Q1","Q2","R2","R3","T2","W2","X2","Y2","Z2","2A2","3D","AT","AM","RT","WT","GT","B","GTH","W","G","F","T","U","INST","INSTL","SNAP","GLOBAL"}
NONFUND = re.compile(r"NOTE|NOTES|BILL|BILLS|TREASURY|TREASURIES|BOND|BONDS|SHS|ADR|COM USD|NPV USD|CORP|CORPORATION|LTD|P\.A\.|AUTOCALL|STRUCTURED", re.I)

def get(url, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return r.read().decode("utf-8","ignore")
        except Exception:
            if a < retries-1:
                time.sleep(3*(a+1))
            else:
                return ""
def ft_search(q):
    url = "https://markets.ft.com/data/search?query=" + urllib.parse.quote(q)
    txt = get(url)
    rows = []
    for m in re.finditer(r'<a href="/data/funds/tearsheet/summary\?s=([A-Z]{2}\d{10}:[A-Z]{2,4})"[^>]*>(.*?)</a>', txt):
        rows.append({"isin_cur": m.group(1), "name": re.sub(r"<[^>]+>","",m.group(2)).strip()})
    return rows

def clean_tokens(name):
    toks = re.split(r"[\s\-/]+", name)
    out = []
    for t in toks:
        t = t.strip(".,'\"()")
        if not t: continue
        tu = t.upper()
        if tu in META or tu in CUR: continue
        if re.fullmatch(r"\d+(\.\d+)?%?", tu): continue
        if re.fullmatch(r"\d[A-Za-z]+", tu): continue
        if len(tu)==1 and tu in set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"): continue
        out.append(t)
    return out

def expected_parts(name):
    toks = re.split(r"\s+", name.strip())
    cur = None
    for t in reversed(toks):
        if t.upper() in CUR:
            cur = t.upper(); break
    # share tokens: trailing tokens that are share-class-ish (multi-char known tokens only, not single letters to be safe)
    share = []
    rest = toks
    if cur:
        rest = toks[:toks.index([x for x in toks if x.upper()==cur][-1])]
    for t in reversed(rest):
        tu = t.upper()
        if tu in {"ACC","ACCUMULATION","DIS","DIST","DISTRIBUTION","INC","INCOME","MDIS","CAP","CAPITAL","NAV","HDG","HGD","HEDGED","AT","AM","RT","WT","GT","INST","INSTL","SNAP","SEL"}:
            share.append(tu)
        else:
            break
    return cur, set(share)

def family_overlap(a_toks, b_toks):
    if not a_toks or not b_toks: return 0.0
    sa, sb = set(a_toks), set(b_toks)
    return len(sa & sb) / max(len(sa), len(sb))

def score_candidate(name, cand):
    cur, share = expected_parts(name)
    c_cur = cand["isin_cur"].split(":")[-1].upper()
    c_toks = clean_tokens(cand["name"])
    n_toks = clean_tokens(name)
    fam = family_overlap(n_toks, c_toks)
    cur_ok = (cur is None) or (c_cur == cur)
    # share presence in candidate name
    c_share = {t.upper() for t in re.split(r"[\s\-/()]+", cand["name"]) if t.upper() in share}
    share_ok = (not share) or (len(c_share)>0)
    return {"family": round(fam,3), "cur_ok": cur_ok, "share_ok": share_ok, "c_cur": c_cur, "exp_cur": cur, "exp_share": sorted(share), "score": round(fam + (0.35 if cur_ok else -0.35) + (0.15 if share_ok else 0), 3)}

def build_variants(name):
    toks = clean_tokens(name)
    vs = []
    vs.append(name[:90])
    if toks:
        vs.append(" ".join(toks[:8]))
        vs.append(" ".join(toks[:5]))
        vs.append(" ".join(toks[:3]))
    # '&' -> and variants
    v2 = []
    for v in vs:
        v2.append(v)
        if "&" in v:
            v2.append(v.replace("&","and"))
    # dedupe
    seen, out = set(), []
    for v in v2:
        k = re.sub(r"\s+"," ", v).strip().lower()
        if k and k not in seen:
            seen.add(k); out.append(v)
    return out

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # warm cookies
    get("https://markets.ft.com/")
    master = list(csv.DictReader(open(D/"eip_master_status.csv", encoding="utf-8-sig")))
    targets = [r for r in master if r["status"] in ("有数据-待人工核","有数据-误配待换","有数据-重试找回(待核)")]
    cov = {r["name"]: r for r in csv.DictReader(open(D/"eip_final_coverage.csv", encoding="utf-8-sig"))}
    qcache = json.loads(QUERY_CACHE.read_text(encoding="utf-8")) if QUERY_CACHE.exists() else {}
    hcache = json.loads(HIST_CACHE.read_text(encoding="utf-8")) if HIST_CACHE.exists() else {}
    print("targets:", len(targets), "query_cache:", len(qcache), flush=True)
    # 1) collect variants & search
    name_cands = {}
    n_search = 0
    for i, r in enumerate(targets, 1):
        name = r["name"]
        cands = []
        for v in build_variants(name):
            if v not in qcache:
                res = ft_search(v)
                qcache[v] = {"results": res}
                n_search += 1
                time.sleep(0.8)
            for c in qcache[v].get("results", []):
                cands.append(c)
        name_cands[name] = cands
        if i % 10 == 0:
            QUERY_CACHE.write_text(json.dumps(qcache, ensure_ascii=False), encoding="utf-8")
            print(f"[{i}/{len(targets)}] searches={n_search}", flush=True)
    QUERY_CACHE.write_text(json.dumps(qcache, ensure_ascii=False), encoding="utf-8")
    print("search done; searches:", n_search, flush=True)
    # 2) score + pick best per name, fetch FT hist for best candidates
    out_rows = []
    for i, r in enumerate(targets, 1):
        name = r["name"]
        cands = name_cands.get(name, [])
        scored = []
        seen = set()
        for c in cands:
            k = c["isin_cur"]
            if k in seen: continue
            seen.add(k)
            sc = score_candidate(name, c)
            sc.update({"isin_cur": k, "ft_name": c["name"]})
            scored.append(sc)
        scored.sort(key=lambda x: -x["score"])
        best = scored[0] if scored else None
        # FT hist check for top 3
        hist = []
        for sc in scored[:3]:
            ic = sc["isin_cur"]
            if ic not in hcache:
                txt = get(f"https://markets.ft.com/data/funds/tearsheet/historical?s={urllib.parse.quote(ic)}")
                trs = re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S)
                rows = []
                for tr in trs:
                    cells = [re.sub(r"<[^>]+>","",c2).strip() for c2 in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                    if len(cells) >= 2 and re.search(r"\d{4}", cells[0]):
                        rows.append(cells[:2])
                hcache[ic] = {"n": len(rows), "first": rows[-1][0][:30] if rows else "", "last": rows[0][0][:30] if rows else "", "last_price": rows[0][1] if rows else ""}
                time.sleep(0.6)
            hist.append({**sc, **hcache.get(ic, {})})
        # verdict
        is_nonfund = bool(NONFUND.search(name))
        if is_nonfund:
            verdict = "非基金-跳过"
        elif not best:
            verdict = "FT无结果"
        elif best["family"] >= 0.5 and best["cur_ok"]:
            verdict = "FT确认" if best["share_ok"] else "FT确认-份额待核"
        elif best["family"] >= 0.5:
            verdict = "币种不符"
        elif best["family"] >= 0.3:
            verdict = "存疑"
        else:
            verdict = "不匹配"
        covr = cov.get(name, {})
        out_rows.append({
            "name": name, "category": r["category"], "master_status": r["status"],
            "cur_symbol": covr.get("symbol",""), "cur_isin": covr.get("isin",""),
            "verdict": verdict, "n_cands": len(scored),
            "best_isin_cur": best["isin_cur"] if best else "",
            "best_ft_name": best["ft_name"] if best else "",
            "best_family": best["family"] if best else "",
            "best_cur_ok": best["cur_ok"] if best else "",
            "best_exp_cur": best.get("exp_cur","") if best else "", "best_c_cur": best.get("c_cur","") if best else "",
            "best_share_ok": best["share_ok"] if best else "",
            "hist_n": hist[0].get("n","") if hist else "",
            "hist_first": hist[0].get("first","") if hist else "",
            "hist_last": hist[0].get("last","") if hist else "",
            "hist_price": hist[0].get("last_price","") if hist else "",
        })
        if i % 10 == 0:
            print(f"[{i}/{len(targets)}] done", flush=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)
    HIST_CACHE.write_text(json.dumps(hcache, ensure_ascii=False), encoding="utf-8")
    print("VERDICTS:", dict(collections.Counter(r["verdict"] for r in out_rows)), flush=True)
    print("DONE ->", OUT, flush=True)

if __name__ == "__main__":
    main()