# -*- coding: utf-8 -*-
"""Phase A: retry Yahoo with clean multi-level queries for the missing set (no-data + wrong)."""
import urllib.request, urllib.parse, json, time, pathlib, csv, re, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.3
CHART_CACHE = BASE / "01_数据" / "eip_retry_chart_cache.json"
OUT = BASE / "01_数据" / "eip_retry_results.csv"

NOISE = {"ACC","DIS","INC","NAV","USD","HKD","EUR","GBP","SGD","AUD","CAD","CNH","CNY","CHF","SEK","DKK","NOK","ZAR","JPY",
    "ACCUMULATION","DISTRIBUTION","CLASS","CLS","SICAV","SHS","COM","NPV","LUX","LUXEMBOURG","UCITS","PLC","SA","CO","CORP",
    "CORPORATION","INCORPORATED","ADR","ADRS","REPR","REPRESENTING","SPONSORED","UNSPONSORED","DEPOSITARY","RECEIPT","RECEIPTS",
    "P.A.","LTD","LIMITED","UNITS","UNIT","HDG","MF","SERIES","SUPER","NOTE","NOTES","BILL","BILLS","TREASURY","TREASURIES",
    "OF","THE","AND","FUND","PORTFOLIO","TRUST","ISSUER","A1","A2","A3","B1","B2","B3","C1","C2","D2","D5","I2","L2","M2","P3",
    "Q1","Q2","R2","R3","T2","W2","X2","Y2","Z2","2A2","3D","AT","AM","RT","WT","GT","GTH","B","C","I","A","X","Y","Z","D","E",
    "F","G","H","J","K","L","M","N","O","P","Q","R","S","T","U","V","W"}
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

def yahoo_search(q, count=12):
    url = "https://query1.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(q) + f"&quotesCount={count}&newsCount=0"
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8")).get("quotes", [])
        except Exception:
            time.sleep(3 * (a + 1))
    return []

def toks(s):
    if not s: return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip(".,'\"()")}
def overlap(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb: return 0.0
    return len(ta & tb) / min(len(ta), len(tb))

def chart(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={int(datetime.datetime(2026,8,15).timestamp())}&interval=1d")
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            res = d["chart"]["result"][0]
            meta = res.get("meta", {})
            ts = res.get("timestamp") or []
            return {"rows": len(ts), "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
                    "shortName": meta.get("shortName", ""), "longName": meta.get("longName", ""),
                    "currency": meta.get("currency", ""), "type": meta.get("instrumentType", "")}
        except Exception:
            time.sleep(3 * (a + 1))
    return {"rows": 0, "first": None, "last": None, "shortName": "", "longName": "", "currency": "", "type": ""}

def main():
    no = list(csv.DictReader(open(BASE / "01_数据" / "eip_no_data_final.csv", encoding="utf-8-sig")))
    wrong = list(csv.DictReader(open(BASE / "01_数据" / "eip_wrong.csv", encoding="utf-8-sig")))
    todo = []
    for r in no:
        todo.append({"name": r["name"], "category": r["category"], "reason": "no-data"})
    for r in wrong:
        todo.append({"name": r["name"], "category": r["category"], "reason": "wrong"})
    # dedup
    seen = set(); uniq = []
    for r in todo:
        if r["name"] not in seen:
            seen.add(r["name"]); uniq.append(r)
    todo = uniq
    print("missing set:", len(todo), flush=True)

    chart_cache = json.loads(CHART_CACHE.read_text(encoding="utf-8")) if CHART_CACHE.exists() else {}
    rows = []
    recovered = 0
    for i, r in enumerate(todo, 1):
        nm = r["name"]
        toks_clean = clean_tokens(nm)
        queries = []
        if len(toks_clean) >= 5: queries.append(" ".join(toks_clean[:5]))
        if len(toks_clean) >= 3: queries.append(" ".join(toks_clean[:3]))
        if len(toks_clean) >= 2: queries.append(" ".join(toks_clean[:2]))
        best_hit, best_q = None, ""
        for q in queries:
            hits = yahoo_search(q)
            if hits:
                # score by overlap with full name; prefer Fund for non-stock-like, Equity for stock-like
                scored = sorted(hits, key=lambda h: (overlap(nm, (h.get("shortname") or "") + " " + (h.get("longname") or ""))), reverse=True)
                best_hit, best_q = scored[0], q
                break
            time.sleep(SLEEP)
        sym = best_hit.get("symbol") if best_hit else ""
        rec = {"name": nm, "category": r["category"], "reason": r["reason"], "query": best_q,
               "symbol": sym, "hit_name": (best_hit.get("shortname") or "") if best_hit else "",
               "hit_type": (best_hit.get("typeDisp") or "") if best_hit else ""}
        if sym:
            if sym not in chart_cache:
                chart_cache[sym] = chart(sym)
                time.sleep(SLEEP)
            chk = chart_cache[sym]
            rec["rows"] = chk["rows"]; rec["first"] = chk["first"]; rec["last"] = chk["last"]
            rec["currency"] = chk["currency"]; rec["yahoo_name"] = (chk["longName"] or chk["shortName"] or "")
            rec["status"] = "recovered" if chk["rows"] > 0 else "no-data"
        else:
            rec.update(rows=0, first="", last="", currency="", yahoo_name="", status="no-data")
        if rec["status"] == "recovered": recovered += 1
        rows.append(rec)
        if i % 15 == 0:
            print(f"[{i}/{len(todo)}] recovered={recovered}", flush=True)
            CHART_CACHE.write_text(json.dumps(chart_cache, ensure_ascii=False), encoding="utf-8")
    CHART_CACHE.write_text(json.dumps(chart_cache, ensure_ascii=False), encoding="utf-8")
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("DONE recovered:", recovered, "/", len(todo))

if __name__ == "__main__":
    main()