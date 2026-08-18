# -*- coding: utf-8 -*-
"""Calibrate FT search on diverse sample names."""
import urllib.request, urllib.parse, re, json, time

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def ft_search(q, limit=12):
    url = "https://markets.ft.com/data/search?query=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode("utf-8", "ignore")
    # parse rows: <a href="/data/funds/tearsheet/summary?s=ISIN:CUR" class="mod-ui-link">NAME</a>
    rows = []
    for m in re.finditer(r'<a href="/data/funds/tearsheet/summary\?s=([A-Z]{2}\d{10}:[A-Z]{2,4})"[^>]*>(.*?)</a>', txt):
        rows.append({"isin_cur": m.group(1), "name": re.sub(r"<[^>]+>", "", m.group(2)).strip()})
    return rows

samples = [
    "AMERICAN AIRLINES COM USD1 USD",
    "UNITED STATES OF AMERICA 0 % TREASURY BILLS 2026-21.07.26 USD",
    "BBVA BOLT GLOBAL RECOVERY NOTE USD",
    "FIDELITY FUNDS AMERICA A ACC USD USD",
    "VANGUARD WHITEHALL INTERNATIONAL HIGH DIV YIEL USD",
    "ALLIANZ GLOBAL ARTIFICIAL INTELLIGENCE RT USD ACC USD",
]
for s in samples:
    try:
        res = ft_search(s)
        print("\nQ:", s[:55])
        print("  results:", len(res))
        for r in res[:6]:
            print("   ", r["isin_cur"], "|", r["name"][:70])
    except Exception as e:
        print("\nQ:", s[:40], "ERR:", e)
    time.sleep(1)