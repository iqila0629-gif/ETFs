# -*- coding: utf-8 -*-
"""Correction pass: currency-preferring FT match -> ISIN -> Yahoo symbol -> chart check -> coverage + audit."""
import urllib.request, urllib.parse, json, time, pathlib, csv, re, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES = list(csv.DictReader(open(BASE / "01_数据" / "eip_fund_names.csv", encoding="utf-8-sig")))
FT = json.loads((BASE / "01_数据" / "eip_ft_search_cache.json").read_text(encoding="utf-8"))
YRES = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_lookup_result.csv", encoding="utf-8-sig"))}
YCHK = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_chart_check.csv", encoding="utf-8-sig"))}
ISIN2SYM = json.loads((BASE / "01_数据" / "eip_isin_symbol_cache.json").read_text(encoding="utf-8")) if (BASE / "01_数据" / "eip_isin_symbol_cache.json").exists() else {}
SYMCHK = json.loads((BASE / "01_数据" / "eip_symbol_chart_cache.json").read_text(encoding="utf-8")) if (BASE / "01_数据" / "eip_symbol_chart_cache.json").exists() else {}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.35

CURRENCIES = {"USD","HKD","EUR","GBP","SGD","AUD","CAD","CNH","CNY","CHF","SEK","DKK","NOK","ZAR","JPY","NZD","TWD","KRW","INR","RMB"}
SHARE_TOKENS = {"ACC","DIS","ACCUMULATION","DISTRIBUTION","INC","AT","AM","RT","WT","GT","P2","P3","A1","I2","L2","M2","R2","T2","W2","2A2","3D","EP","S14","S1","S","B","C","I","A","X","Y","Z","D","E","F","G","H","J","K","L","M","N","O","P","Q","R","T","U","V","W"}
NOISE = CURRENCIES | SHARE_TOKENS | {"FUND","PORTFOLIO","SICAV","LUX","LUXEMBOURG","CLASS","CLS","UCITS","PLC","SA","CO","LTD","LIMITED","THE","OF","AND","SERIES","INSTITUTIONAL","RETAIL","UNITS","HDG","MF","NAV","FCP","INVESTORS","INVESTOR"}

def toks(s):
    if not s: return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip(".,'\"()")}
def theme(s): return toks(s) - NOISE
def class_toks(s):
    ts = toks(s); return {t for t in ts if t in SHARE_TOKENS or t in CURRENCIES}
def accdis(ts):
    if "ACC" in ts or "ACCUMULATION" in ts: return "ACC"
    if "DIS" in ts or "DISTRIBUTION" in ts: return "DIS"
    return None
def cur_of(s):
    return next((c for c in CURRENCIES if c in toks(s)), None)

def score(our, ftname, ftcur):
    ot, ft = theme(our), theme(ftname)
    if not ot or not ft: return 0.0
    inter = len(ot & ft)
    if inter == 0: return 0.0
    s = inter / min(len(ot), len(ft)) + 0.5 * (inter / len(ot))
    oc, fc = class_toks(our), class_toks(ftname)
    if cur_of(our) and cur_of(our) == ftcur.upper(): s += 0.8
    letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    ol = {t for t in oc if t in letters}; fl = {t for t in fc if t in letters}
    if ol and fl:
        s += 0.4 if ol == fl else -0.8
    a, b = accdis(oc), accdis(fc)
    if a and b: s += 0.4 if a == b else -1.2
    return round(s, 3)

def yahoo_search_isin(isin):
    url = ("https://query1.finance.yahoo.com/v1/finance/search?q=" + isin + "&quotesCount=10&newsCount=0")
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            qs = d.get("quotes", [])
            funds = [q for q in qs if (q.get("typeDisp") or "").lower() == "fund"]
            pool = funds if funds else qs
            if not pool: return None
            q = pool[0]
            return {"symbol": q.get("symbol"), "shortname": q.get("shortname"), "type": q.get("typeDisp"), "exch": q.get("exchange")}
        except Exception:
            time.sleep(3 * (a + 1))
    return None

def chart_meta(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1=0&period2={int(datetime.datetime(2026,8,15).timestamp())}&interval=1d")
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

# ---- Step 1: currency-preferring FT best match ----
merged = []
for r in NAMES:
    nm = r["name"]
    ft_entries = [x for x in FT.get(nm, {}).get("results", []) if "error" not in x]
    our_cur = cur_of(nm)
    ft_best = None
    if ft_entries:
        scored = sorted(ft_entries, key=lambda x: score(nm, x["name"], x["isin_cur"].split(":")[1]), reverse=True)
        best = scored[0]
        sc = score(nm, best["name"], best["isin_cur"].split(":")[1])
        # prefer currency match: pick best among same-currency if any
        if our_cur:
            same_cur = [x for x in scored if x["isin_cur"].split(":")[1].upper() == our_cur]
            if same_cur:
                best = same_cur[0]
                sc = score(nm, best["name"], best["isin_cur"].split(":")[1])
        if sc >= 0.7:
            ft_best = {"name": best["name"], "isin_cur": best["isin_cur"], "score": sc}
    merged.append({"name": nm, "category": r["category"],
                   "ft_best_name": ft_best["name"] if ft_best else "",
                   "ft_isin_cur": ft_best["isin_cur"] if ft_best else "",
                   "ft_score": ft_best["score"] if ft_best else "",
                   "yahoo_name_sym": YRES.get(nm, {}).get("best_symbol", "")})

with open(BASE / "01_数据" / "eip_merged_candidates.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(merged[0].keys())); w.writeheader(); w.writerows(merged)
n_ft = sum(1 for r in merged if r["ft_best_name"])
print("step1 ft best match:", n_ft, flush=True)

# ---- Step 2: ISIN -> Yahoo symbol (cache by ISIN) ----
for i, r in enumerate(merged, 1):
    if not r["ft_isin_cur"]: continue
    isin = r["ft_isin_cur"].split(":")[0]
    if isin not in ISIN2SYM:
        ISIN2SYM[isin] = yahoo_search_isin(isin)
        time.sleep(SLEEP)
    if i % 30 == 0:
        print(f"step2 [{i}/{len(merged)}]", flush=True)
        (BASE / "01_数据" / "eip_isin_symbol_cache.json").write_text(json.dumps(ISIN2SYM, ensure_ascii=False), encoding="utf-8")
(BASE / "01_数据" / "eip_isin_symbol_cache.json").write_text(json.dumps(ISIN2SYM, ensure_ascii=False), encoding="utf-8")
print("step2 isins mapped:", sum(1 for v in ISIN2SYM.values() if v), "/", len(ISIN2SYM), flush=True)

# ---- Step 3: chart check final symbols (cache by symbol) ----
final_rows = []
for i, r in enumerate(merged, 1):
    nm = r["name"]
    isin = (r["ft_isin_cur"] or "").split(":")[0]
    isin_sym = (ISIN2SYM.get(isin) or {}).get("symbol", "") if isin else ""
    ysym = r["yahoo_name_sym"]
    if isin_sym:
        sym = isin_sym; source = "FT-ISIN->Yahoo"
    elif ysym:
        sym = ysym; source = "Yahoo按名称"
    else:
        sym = ""; source = "无结果"
    if sym:
        if sym not in SYMCHK:
            SYMCHK[sym] = chart_meta(sym)
            time.sleep(SLEEP)
        chk = SYMCHK[sym]
        has = chk["rows"] > 0
    else:
        chk = {"rows": 0}; has = False
    status = "有数据" if has else "无数据"
    if not has and isin:
        source = "有ISIN无Yahoo数据"
    final_rows.append({"name": nm, "category": r["category"], "status": status, "source": source,
                       "symbol": sym, "isin": isin, "ft_name": r["ft_best_name"],
                       "yahoo_name_sym": ysym, "rows": chk.get("rows", 0),
                       "first": chk.get("first"), "last": chk.get("last"),
                       "yahoo_name": ((chk.get("longName") or chk.get("shortName") or "")),
                       "yahoo_currency": chk.get("currency", ""), "yahoo_type": chk.get("type", "")})
    if i % 30 == 0:
        print(f"step3 [{i}/{len(merged)}]", flush=True)
        (BASE / "01_数据" / "eip_symbol_chart_cache.json").write_text(json.dumps(SYMCHK, ensure_ascii=False), encoding="utf-8")
(BASE / "01_数据" / "eip_symbol_chart_cache.json").write_text(json.dumps(SYMCHK, ensure_ascii=False), encoding="utf-8")

with open(BASE / "01_数据" / "eip_final_coverage.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(final_rows[0].keys())); w.writeheader(); w.writerows(final_rows)
from collections import Counter
print("status:", dict(Counter(r["status"] for r in final_rows)))
print("source:", dict(Counter(r["source"] for r in final_rows)))