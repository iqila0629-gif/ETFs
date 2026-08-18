# -*- coding: utf-8 -*-
"""按 (name, symbol) 列表通过 Yahoo 重拉/新拉基金价格（cookie+crumb 鉴权，断点续跑）。
用法: python yahoo_repull.py <input_csv: name,symbol[,reason]>  <out_dir>
"""
import urllib.request, urllib.parse, json, time, pathlib, csv, sys, http.cookiejar, re

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    in_csv = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path(sys.argv[2])
    PERIOD1 = 820454400
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125"}
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def get(url, retries=3):
        for a in range(retries):
            try:
                req = urllib.request.Request(url, headers=UA)
                with opener.open(req, timeout=40) as r:
                    return r.read()
            except Exception:
                if a < retries-1: time.sleep(3*(a+1))
                else: raise
    try: get("https://fc.yahoo.com")
    except Exception: pass
    try:
        crumb = get("https://query1.finance.yahoo.com/v1/test/getcrumb").decode("utf-8","ignore").strip()
    except Exception:
        crumb = ""
    rows = list(csv.DictReader(open(in_csv, encoding="utf-8-sig")))
    out_dir.mkdir(parents=True, exist_ok=True)
    log = []
    done = 0; fail = 0
    for i, r in enumerate(rows, 1):
        name, sym = r["name"], r["symbol"]
        if not sym:
            log.append({**r, "status": "NO_SYMBOL", "rows": ""}); continue
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={PERIOD1}&period2={int(time.time())}&interval=1d&crumb={urllib.parse.quote(crumb)}"
            d = json.loads(get(url).decode("utf-8","ignore"))
            res = d["chart"]["result"][0]
            ts = res["timestamp"]; q = res["indicators"]["quote"][0]
            adj = res["indicators"].get("adjclose",[{}])[0].get("adjclose",[])
            lines = ["Date,Open,High,Low,Close,Volume,Adj Close"]
            for j in range(len(ts)):
                def val(arr): return f"{arr[j]:.6f}" if j < len(arr) and arr[j] is not None else ""
                dstr = time.strftime("%Y-%m-%d", time.gmtime(ts[j]))
                lines.append(f"{dstr},{val(q.get('open',[]))},{val(q.get('high',[]))},{val(q.get('low',[]))},{val(q.get('close',[]))},{val(q.get('volume',[]))},{val(adj)}")
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)
            (out_dir / (safe_name + ".csv")).write_text("\n".join(lines) + "\n", encoding="utf-8")
            log.append({**r, "status": "OK", "rows": len(ts)})
            done += 1
            print(f"[{i}/{len(rows)}] OK {sym} rows={len(ts)} :: {name[:40]}", flush=True)
        except Exception as e:
            log.append({**r, "status": "FAIL", "rows": "", "err": str(e)[:150]})
            fail += 1
            print(f"[{i}/{len(rows)}] FAIL {sym} :: {name[:40]} :: {e}", flush=True)
        time.sleep(0.4)
    logpath = in_csv.with_suffix(".repull_log.csv")
    keys = list(rows[0].keys()) + (["status","rows","err"] if any("err" in x for x in log) else ["status","rows"])
    with open(logpath, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(log)
    print(f"DONE ok={done} fail={fail} -> log {logpath}")

if __name__ == "__main__":
    main()