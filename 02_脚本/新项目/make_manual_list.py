# -*- coding: utf-8 -*-
"""Generate manual download task list for remaining funds."""
import pathlib, csv, urllib.parse

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
SCORED = {r["name"]: r for r in csv.DictReader(open(BASE / "01_数据" / "eip_remaining_scored.csv", encoding="utf-8-sig"))}
REMAIN = list(csv.DictReader(open(BASE / "01_数据" / "eip_remaining_missing.csv", encoding="utf-8-sig")))
RECOVERED_STOCKS = {"BK OF AMERICA CORP COM USD0.01 USD", "DELL INTERNATIONAL LLC USD",
                    "EVOLUTION SHS UNSPONSORED AMERICAN DEPOSITARY RECEIPT REPR 1 SH USD",
                    "UNILEVER SHS SPONSORED AMERICAN DEPOSITARY SHARES REPR 1 SH USD"}

def q(s): return urllib.parse.quote(s)

rows = []
for r in REMAIN:
    nm = r["name"]
    if nm in RECOVERED_STOCKS:
        continue
    sc = SCORED.get(nm, {})
    isin_cur = sc.get("cand_isin", "")
    isin = isin_cur.split(":")[0] if isin_cur else ""
    cur = isin_cur.split(":")[1] if ":" in isin_cur else ""
    ft_search = f"https://markets.ft.com/data/search?query={q(nm)}"
    fundinfo = f"https://www.fundinfo.com/en/search?query={q(nm)}"
    wso = f"https://www.wallstreet-online.de/suche?suchbegriff={q(nm)}"
    ft_hist = f"https://markets.ft.com/data/funds/tearsheet/historical?s={isin_cur}" if isin_cur else ""
    rows.append({
        "name": nm, "category": r["category"], "kind": r["kind"],
        "cand_isin": isin_cur, "isin_confident": "待核" if isin_cur else "",
        "ft_hist_url": ft_hist,
        "ft_search_url": ft_search,
        "fundinfo_url": fundinfo,
        "wallstreet_url": wso,
        "note": "人工搜索确认份额/币种后下载" if r["kind"] == "基金" else ("免费源无解" if r["kind"] in ("债券/票据", "结构性") else ""),
    })

with open(BASE / "01_数据" / "eip_manual_download.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

from collections import Counter
print("manual list rows:", len(rows))
print(dict(Counter(r["kind"] for r in rows)))
print("with candidate ISIN:", sum(1 for r in rows if r["cand_isin"]))