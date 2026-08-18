# -*- coding: utf-8 -*-
"""Re-score FT remaining results with proper matcher; keep only high-confidence ISINs."""
import pathlib, csv, json, re

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
REMAIN = list(csv.DictReader(open(BASE / "01_数据" / "eip_remaining_missing.csv", encoding="utf-8-sig")))
FTREM = json.loads((BASE / "01_数据" / "eip_ft_remaining_cache.json").read_text(encoding="utf-8"))

CURRENCIES = {"USD","HKD","EUR","GBP","SGD","AUD","CAD","CNH","CNY","CHF","SEK","DKK","NOK","ZAR","JPY","NZD","TWD","KRW","INR","RMB"}
SHARE = {"ACC","DIS","ACCUMULATION","DISTRIBUTION","INC","AT","AM","RT","WT","GT","P2","P3","A1","I2","L2","M2","R2","T2","W2","2A2","3D","EP","S14","S1","S","B","C","I","A","X","Y","Z","D","E","F","G","H","J","K","L","M","N","O","P","Q","R","T","U","V","W"}
NOISE = CURRENCIES | SHARE | {"FUND","PORTFOLIO","SICAV","LUX","LUXEMBOURG","CLASS","CLS","UCITS","PLC","SA","CO","LTD","LIMITED","THE","OF","AND","SERIES","INSTITUTIONAL","RETAIL","UNITS","HDG","MF","NAV","FCP","INVESTORS","INVESTOR","FDS","SEL","GLOBAL","INTERNATIONAL","MGMT","MANAGEMENT","INVESTMENT","ASSET","INV","IF","SA"}

def toks(s):
    if not s: return set()
    return {t.strip(".,'\"()").upper() for t in re.split(r"[\s\-/]+", str(s)) if t.strip(".,'\"()")}
def theme(s): return toks(s) - NOISE
def cur_of(s): return next((c for c in CURRENCIES if c in toks(s)), None)
def accdis(ts):
    if "ACC" in ts or "ACCUMULATION" in ts: return "ACC"
    if "DIS" in ts or "DISTRIBUTION" in ts: return "DIS"
    return None
def score(our, ftname, ftcur):
    ot, ft = theme(our), theme(ftname)
    if not ot or not ft: return 0.0
    inter = len(ot & ft)
    if inter == 0: return 0.0
    s = inter / min(len(ot), len(ft)) + 0.5 * (inter / len(ot))
    oc = {t for t in toks(our) if t in SHARE or t in CURRENCIES}
    fc = {t for t in toks(ftname) if t in SHARE or t in CURRENCIES}
    if cur_of(our) and cur_of(our) == ftcur.upper(): s += 0.8
    letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    ol = {t for t in oc if t in letters}; fl = {t for t in fc if t in letters}
    if ol and fl: s += 0.4 if ol == fl else -0.8
    a, b = accdis(oc), accdis(fc)
    if a and b: s += 0.4 if a == b else -1.2
    return round(s, 3)

out = []
for r in REMAIN:
    if r["kind"] != "基金": continue
    nm = r["name"]
    res = FTREM.get(nm, [])
    best = None
    if res:
        scored = sorted(res, key=lambda x: score(nm, x["name"], x["isin_cur"].split(":")[1]), reverse=True)
        b = scored[0]
        sc = score(nm, b["name"], b["isin_cur"].split(":")[1])
        our_cur = cur_of(nm)
        if our_cur:
            same = [x for x in scored if x["isin_cur"].split(":")[1].upper() == our_cur]
            if same:
                b = same[0]; sc = score(nm, b["name"], b["isin_cur"].split(":")[1])
        if sc >= 0.7:
            best = {"isin_cur": b["isin_cur"], "name": b["name"], "score": sc}
    out.append({"name": nm, "cand_isin": best["isin_cur"] if best else "", "ft_name": best["name"] if best else "",
                "score": best["score"] if best else "", "category": r["category"]})

with open(BASE / "01_数据" / "eip_remaining_scored.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name","category","cand_isin","ft_name","score"])
    w.writeheader(); w.writerows(out)
print("funds:", len(out), "| high-confidence ISIN:", sum(1 for r in out if r["cand_isin"]))
for r in out:
    if r["cand_isin"]:
        print(f"  {r['cand_isin']:20} {r['score']:6} {r['name'][:55]:57} | {r['ft_name'][:45]}")