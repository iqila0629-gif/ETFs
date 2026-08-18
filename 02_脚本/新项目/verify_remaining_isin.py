# -*- coding: utf-8 -*-
"""For remaining funds with candidate ISIN: Yahoo-by-ISIN retry + FT summary confirm."""
import urllib.request, urllib.parse, json, time, pathlib, csv, re, datetime

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
REMAIN = list(csv.DictReader(open(BASE / "01_数据" / "eip_remaining_missing.csv", encoding="utf-8-sig")))
FTREM = json.loads((BASE / "01_数据" / "eip_ft_remaining_cache.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SLEEP = 0.4

def yahoo_isin(isin):
    url = "https://query1.finance.yahoo.com/v1/finance/search?q=" + isin + "&quotesCount=10&newsCount=0"
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            qs = d.get("quotes", [])
            funds = [q for q in qs if (q.get("typeDisp") or "").lower() == "fund"]
            pool = funds if funds else qs
            return pool[0] if pool else None
        except Exception:
            time.sleep(3 * (a + 1))
    return None

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
            return {"rows": len(ts), "shortName": meta.get("shortName", ""), "longName": meta.get("longName", ""),
                    "currency": meta.get("currency", "")}
        except Exception:
            time.sleep(3 * (a + 1))
    return {"rows": 0, "shortName": "", "longName": "", "currency": ""}

def ft_summary(isin_cur):
    url = "https://markets.ft.com/data/funds/tearsheet/summary?s=" + urllib.parse.quote(isin_cur)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode("utf-8", "ignore")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", txt)
        return (m.group(1).strip() if m else ""), True
    except Exception:
        return "", False

rows = []
for r in REMAIN:
    if r["kind"] != "基金":
        continue
    nm = r["name"]
    ftres = FTREM.get(nm, [])
    isin_cur = ftres[0]["isin_cur"] if ftres else r.get("cand_isin", "")
    isin = isin_cur.split(":")[0] if isin_cur else ""
    rec = {"name": nm, "category": r["category"], "cand_isin": isin_cur, "ft_name": ftres[0]["name"] if ftres else r.get("cand_ft_name", "")}
    if isin:
        q = yahoo_isin(isin)
        if q:
            chk = chart(q["symbol"])
            rec["yahoo_sym"] = q["symbol"]; rec["yahoo_name"] = (chk["longName"] or chk["shortName"] or (q.get("shortname") or ""))
            rec["yahoo_rows"] = chk["rows"]; rec["yahoo_cur"] = chk["currency"]
        else:
            rec.update(yahoo_sym="", yahoo_name="", yahoo_rows=0, yahoo_cur="")
        fn, ok = ft_summary(isin_cur)
        rec["ft_confirmed"] = ok; rec["ft_page_name"] = fn
    else:
        rec.update(yahoo_sym="", yahoo_name="", yahoo_rows=0, yahoo_cur="", ft_confirmed=False, ft_page_name="")
    rows.append(rec)
    time.sleep(SLEEP)

with open(BASE / "01_数据" / "eip_remaining_verify.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

rec_auto = sum(1 for r in rows if r.get("yahoo_rows", 0) > 0)
ft_ok = sum(1 for r in rows if r.get("ft_confirmed"))
print("funds with ISIN:", len(rows), "| auto-recovered via Yahoo-by-ISIN:", rec_auto, "| FT page confirmed:", ft_ok)
for r in rows:
    print(("REC " if r.get("yahoo_rows", 0) > 0 else "    ") + f"{r['cand_isin']:20} {r['name'][:48]:50} | yahoo={r.get('yahoo_sym','')} rows={r.get('yahoo_rows',0)} | ft_ok={r.get('ft_confirmed')}")