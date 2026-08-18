# -*- coding: utf-8 -*-
"""刷新 19 ETF 收益面板到最新日期：保留旧历史，追加 2026-08-07 之后的新交易日。"""
import urllib.request, urllib.parse, json, time, pathlib, sys, http.cookiejar, io
import pandas as pd
import numpy as np

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
OLD = BASE / "01_数据" / "event_study_inputs" / "panel_etf_returns_adj.csv"
OUT = BASE / "01_数据" / "event_study_inputs" / "panel_etf_returns_adj_v2.csv"
ORIGINAL19 = ["SPY","QQQ","IWM","TLT","TIP","EEM","LQD","HYG","UUP","SLV","JNK","GLD","GDX","XLV","XLU","XLE","XLF","XLK","FXY"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125", "Accept": "application/json,text/plain,*/*"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(url, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return r.read()
        except Exception:
            if a < tries-1: time.sleep(2*(a+1))
            else: raise
crumb = ""
try: get("https://fc.yahoo.com")
except Exception: pass
try:
    crumb = get("https://query1.finance.yahoo.com/v1/test/getcrumb").decode("utf-8","ignore").strip()
except Exception as e:
    print("crumb FAIL", e, flush=True)

def fetch_adj(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1=1780272000&period2={int(time.time())}&interval=1d&crumb={urllib.parse.quote(crumb)}"  # 2026-06-01
    d = json.loads(get(url).decode("utf-8","ignore"))
    res = d["chart"]["result"][0]
    ts = res.get("timestamp") or []
    adj = (res["indicators"].get("adjclose", [{}])[0] or {}).get("adjclose", [])
    out = {}
    for i in range(len(ts)):
        if i < len(adj) and adj[i] is not None:
            dt = time.strftime("%Y-%m-%d", time.gmtime(ts[i]))
            out[dt] = float(adj[i])
    return out

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    old = pd.read_csv(OLD)
    old["Date"] = old["Date"].astype(str).str[:10]
    old = old.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)
    old_last = old["Date"].iloc[-1]
    print("old ETF panel:", len(old), "last:", old_last, flush=True)
    new_rows = {}
    for sym in ORIGINAL19:
        d = fetch_adj(sym)
        # pct change over fetched window, keep only dates > old_last
        s = pd.Series(d).sort_index()
        ret = s.pct_change() * 100.0
        for dt, v in ret.items():
            if dt > old_last and pd.notna(v):
                new_rows.setdefault(dt, {})[sym] = float(v)
        time.sleep(0.3)
        print("  fetched", sym, "last:", max(d) if d else "-", flush=True)
    ndates = sorted(new_rows.keys())
    print("new dates to append:", len(ndates), ndates[:3], "...", ndates[-3:] if ndates else "", flush=True)
    if ndates:
        add = pd.DataFrame([{"Date": dt, **new_rows[dt]} for dt in ndates])
        panel = pd.concat([old, add], ignore_index=True).sort_values("Date").reset_index(drop=True)
    else:
        panel = old
    panel.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("saved:", OUT, "rows:", len(panel), "range:", panel["Date"].iloc[0], "->", panel["Date"].iloc[-1])
    print("any NaN in ETF cols:", int(panel[ORIGINAL19].isna().sum().sum()))

if __name__ == "__main__":
    main()