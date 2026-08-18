# -*- coding: utf-8 -*-
"""Merge FT ISIN results with Yahoo name matches (v2: single letters as share tokens)."""
import json, pathlib, csv, re

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES = list(csv.DictReader(open(BASE / "01_数据" / "eip_fund_names.csv", encoding="utf-8-sig")))
FT = json.loads((BASE / "01_数据" / "eip_ft_search_cache.json").read_text(encoding="utf-8"))
YRES = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_yahoo_lookup_result.csv", encoding="utf-8-sig"))}

CURRENCIES = {"USD", "HKD", "EUR", "GBP", "SGD", "AUD", "CAD", "CNH", "CNY", "CHF", "SEK", "DKK", "NOK", "ZAR", "JPY", "NZD", "TWD", "KRW", "INR", "RMB"}
SHARE_TOKENS = {"ACC", "DIS", "ACCUMULATION", "DISTRIBUTION", "INC", "AT", "AM", "RT", "WT", "GT", "P2", "P3", "A1", "I2", "L2", "M2", "R2", "T2", "W2", "2A2", "3D", "EP", "S14", "S1", "S", "B", "C", "I", "A", "X", "Y", "Z", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "T", "U", "V", "W"}
NOISE = CURRENCIES | SHARE_TOKENS | {"FUND", "PORTFOLIO", "SICAV", "LUX", "LUXEMBOURG", "CLASS", "CLS", "UCITS", "PLC", "SA", "CO", "LTD", "LIMITED", "THE", "OF", "AND", "SERIES", "INSTITUTIONAL", "RETAIL", "UNITS", "HDG", "MF", "NAV", "FCP", "INVESTORS", "INVESTOR"}

def toks(s):
    if not s:
        return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip(".,'\"()")}

def theme_tokens(s):
    return toks(s) - NOISE

def class_tokens(s):
    ts = toks(s)
    return {t for t in ts if t in SHARE_TOKENS or t in CURRENCIES}

def accdis(ts):
    if "ACC" in ts or "ACCUMULATION" in ts:
        return "ACC"
    if "DIS" in ts or "DISTRIBUTION" in ts:
        return "DIS"
    return None

def score(our, ftname, ftcur):
    ot, ft = theme_tokens(our), theme_tokens(ftname)
    if not ot or not ft:
        return 0.0
    inter = len(ot & ft)
    if inter == 0:
        return 0.0
    s = inter / min(len(ot), len(ft)) + 0.5 * (inter / len(ot))
    oc, fc = class_tokens(our), class_tokens(ftname)
    our_cur = next((c for c in CURRENCIES if c in toks(our)), None)
    if our_cur and our_cur == ftcur.upper():
        s += 0.6
    # share-letter match (e.g., our I vs ft S are different -> penalty)
    letters = {"A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"}
    ol = {t for t in oc if t in letters}
    fl = {t for t in fc if t in letters}
    if ol and fl and ol != fl:
        s -= 0.8
    else:
        s += 0.3 * len(ol & fl)
    a, b = accdis(oc), accdis(fc)
    if a and b:
        s += 0.4 if a == b else -1.2
    return round(s, 3)

rows = []
for r in NAMES:
    nm = r["name"]
    ft_entries = [x for x in FT.get(nm, {}).get("results", []) if "error" not in x]
    ft_best = None
    if ft_entries:
        best = max(ft_entries, key=lambda x: score(nm, x["name"], x["isin_cur"].split(":")[1]))
        sc = score(nm, best["name"], best["isin_cur"].split(":")[1])
        if sc >= 0.8:
            ft_best = {"name": best["name"], "isin_cur": best["isin_cur"], "score": sc}
    yahoo_sym = YRES.get(nm, {}).get("best_symbol", "")
    rows.append({
        "name": nm, "category": r["category"],
        "ft_found": bool(ft_entries),
        "ft_best_name": ft_best["name"] if ft_best else "",
        "ft_isin_cur": ft_best["isin_cur"] if ft_best else "",
        "ft_score": ft_best["score"] if ft_best else "",
        "yahoo_name_sym": yahoo_sym,
    })

out = BASE / "01_数据" / "eip_merged_candidates.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

n_ft = sum(1 for r in rows if r["ft_best_name"])
print("names:", len(rows), "| ft best match:", n_ft)
# show share-class sanity for the previously noted cases
for nm in ["AB GLOBAL HIGH YIELD PORTFOLIO I INC USD", "AB INTERNATIONAL HEALTH CARE PORTFOLIO C ACC USD", "ABRDN SICAV I - GLOBAL DYNAMIC DIVIDEND FUND X INC USD USD"]:
    r = next(x for x in rows if x["name"] == nm)
    print(f"\n{nm[:50]}\n   -> {r['ft_isin_cur']} | {r['ft_best_name'][:70]}")