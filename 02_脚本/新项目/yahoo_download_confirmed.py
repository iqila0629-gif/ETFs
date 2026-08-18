# -*- coding: utf-8 -*-
"""批量下载 77 支已确认基金：Yahoo v8 chart (cookie+crumb) -> 新项目_基金价格/<名>.csv + quote 元数据 QA。"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
TODO = BASE / "01_数据" / "eip_77_confirm_todo.csv"
OUT = BASE / "01_数据" / "新项目_基金价格"
LOG = BASE / "01_数据" / "eip_77_download_log.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125", "Accept": "application/json,text/plain,*/*"}
PERIOD1 = 820454400  # 1996-01-01
SLEEP = 0.3

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def get(url, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with opener.open(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            # still consume body? not needed
            if a < retries-1:
                time.sleep(3*(a+1))
            else:
                raise
        except Exception as e:
            if a < retries-1:
                time.sleep(3*(a+1))
            else:
                raise

# init session: cookies + crumb
crumb = ""
try:
    get("https://fc.yahoo.com")
except Exception:
    pass
try:
    crumb = get("https://query1.finance.yahoo.com/v1/test/getcrumb").decode("utf-8","ignore").strip()
    print("crumb:", crumb, flush=True)
except Exception as e:
    print("crumb FAIL:", e, flush=True)

def fetch_chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={PERIOD1}&period2={int(time.time())}&interval=1d&crumb={urllib.parse.quote(crumb)}"
    d = json.loads(get(url).decode("utf-8","ignore"))
    res = d["chart"]["result"][0]
    meta = res.get("meta", {})
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
    for i in range(len(ts)):
        def val(arr):
            return f"{arr[i]:.6f}" if i < len(arr) and arr[i] is not None else ""
        dstr = time.strftime("%Y-%m-%d", time.gmtime(ts[i]))
        lines.append(f"{dstr},{val(q.get('open',[]))},{val(q.get('high',[]))},{val(q.get('low',[]))},{val(q.get('close',[]))},{val(q.get('volume',[]))},{val(adj)}")
    return "\n".join(lines), meta

def fetch_quote(sym):
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={urllib.parse.quote(sym)}&crumb={urllib.parse.quote(crumb)}"
    d = json.loads(get(url).decode("utf-8","ignore"))
    q = (d.get("quoteResponse") or {}).get("result") or []
    return q[0] if q else {}

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(open(TODO, encoding="utf-8-sig")))
    OUT.mkdir(exist_ok=True)
    log_rows = []
    sym_cache = {}
    for i, r in enumerate(rows, 1):
        name, sym = r["name"], r["symbol"]
        try:
            if sym not in sym_cache:
                chart, meta = fetch_chart(sym)
                try:
                    quote = fetch_quote(sym)
                except Exception:
                    quote = {}
                sym_cache[sym] = (chart, meta, quote)
                time.sleep(SLEEP)
            chart, meta, quote = sym_cache[sym]
            fn = OUT / (name + ".csv")
            fn.write_text(chart + "\n", encoding="utf-8")
            nrows = chart.count("\n") - 1
            log_rows.append({"name": name, "symbol": sym, "status": "OK", "rows": nrows,
                             "yahoo_longname": quote.get("longName") or quote.get("shortName") or meta.get("longName") or meta.get("shortName",""),
                             "currency": quote.get("currency") or meta.get("currency",""),
                             "quoteType": quote.get("quoteType") or meta.get("instrumentType",""),
                             "exchange": quote.get("fullExchangeName") or meta.get("exchangeName","")})
            print(f"[{i}/{len(rows)}] OK {sym} rows={nrows} :: {name[:40]}", flush=True)
        except Exception as e:
            log_rows.append({"name": name, "symbol": sym, "status": "FAIL", "rows": "", "yahoo_longname": "", "currency": "", "quoteType": "", "exchange": "", "note": str(e)[:200]})
            print(f"[{i}/{len(rows)}] FAIL {sym} :: {name[:40]} :: {e}", flush=True)
        time.sleep(SLEEP)
    with open(LOG, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        w.writeheader(); w.writerows(log_rows)
    ok = sum(1 for r in log_rows if r["status"]=="OK")
    print("DONE ok:", ok, "/", len(rows))

if __name__ == "__main__":
    main()