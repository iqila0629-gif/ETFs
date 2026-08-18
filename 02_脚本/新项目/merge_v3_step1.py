# -*- coding: utf-8 -*-
"""Step 1 only: currency-preferring FT re-match + diff vs old merged."""
import json, pathlib, csv, re
BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
NAMES = list(csv.DictReader(open(BASE / "01_数据" / "eip_fund_names.csv", encoding="utf-8-sig")))
FT = json.loads((BASE / "01_数据" / "eip_ft_search_cache.json").read_text(encoding="utf-8"))
OLD = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_merged_candidates.csv", encoding="utf-8-sig"))}

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
def cur_of(s): return next((c for c in CURRENCIES if c in toks(s)), None)

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
    if ol and fl: s += 0.4 if ol == fl else -0.8
    a, b = accdis(oc), accdis(fc)
    if a and b: s += 0.4 if a == b else -1.2
    return round(s, 3)

merged = []
changed = 0
for r in NAMES:
    nm = r["name"]
    ft_entries = [x for x in FT.get(nm, {}).get("results", []) if "error" not in x]
    our_cur = cur_of(nm)
    ft_best = None
    if ft_entries:
        scored = sorted(ft_entries, key=lambda x: score(nm, x["name"], x["isin_cur"].split(":")[1]), reverse=True)
        best = scored[0]
        if our_cur:
            same_cur = [x for x in scored if x["isin_cur"].split(":")[1].upper() == our_cur]
            if same_cur: best = same_cur[0]
        sc = score(nm, best["name"], best["isin_cur"].split(":")[1])
        if sc >= 0.7:
            ft_best = {"name": best["name"], "isin_cur": best["isin_cur"], "score": sc}
    old = OLD.get(nm, {})
    old_isin = (old.get("ft_isin_cur") or "").split(":")[0]
    new_isin = (ft_best["isin_cur"] if ft_best else "").split(":")[0]
    if old_isin != new_isin:
        changed += 1
    merged.append({"name": nm, "category": r["category"],
                   "ft_best_name": ft_best["name"] if ft_best else "",
                   "ft_isin_cur": ft_best["isin_cur"] if ft_best else "",
                   "ft_score": ft_best["score"] if ft_best else ""})

with open(BASE / "01_数据" / "eip_merged_candidates.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(merged[0].keys())); w.writeheader(); w.writerows(merged)
print("ft best match:", sum(1 for r in merged if r["ft_best_name"]))
print("ISIN changed vs old:", changed)
# print new currency matches for previously currency-mismatched
for nm in ["AB GLOBAL HIGH YIELD PORTFOLIO I INC USD", "ALLIANZ GLOBAL INV CHINA EQUITY A USD DIS USD"]:
    r = next(x for x in merged if x["name"] == nm)
    print(nm[:45], "->", r["ft_isin_cur"], "|", r["ft_best_name"][:60])