# -*- coding: utf-8 -*-
"""EODHD 批量拉取 71 支待下载基金历史净值（免费版 20 次/天，可断点续跑）。
用法：
  python eodhd_batch.py --max-calls 18          # 每次最多用 N 次 API 调用
  python eodhd_batch.py --only "ABERDEEN ..."   # 只处理指定基金
输出：
  01_数据/api_download/<基金名>.csv   (Date,Open,High,Low,Close,Adjusted_close)
  01_数据/eip_api_download_log.csv   (处理日志)
"""
import json, time, csv, pathlib, urllib.request, urllib.parse, re, sys

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
OUT_DIR = BASE / "01_数据" / "api_download"
LOG_CSV = BASE / "01_数据" / "eip_api_download_log.csv"
OUT_DIR.mkdir(exist_ok=True)
cfg = json.loads((BASE / "01_数据" / "api_keys.json").read_text(encoding="utf-8"))
KEYS = cfg["eodhd_list"]
_used = {k: 0 for k in KEYS}
_exhausted = set()

def pick_key():
    avail = [k for k in KEYS if k not in _exhausted]
    if not avail:
        return None
    return min(avail, key=lambda k: _used[k])

def mark_exhausted(k):
    _exhausted.add(k)

# ---------------------------------------------------------------- 基金 -> 拉取线索
# isin: 可信 ISIN（去币种）；hint: EODHD 站内搜索词；suffix: 备选交易所后缀
MAP = {
"ABERDEEN STD - NORTH AMERICAN SMALLER COMPANIES FUND I ACC USD USD": dict(isin="", hint="abrdn American Growth", suffix=["EUFUND"]),
"ALLIANCE BERNSTEIN AMERICAN INCOME PORTFOLIO INC USD": dict(isin="", hint="AB - American Income Portfolio", suffix=["EUFUND"]),
"ALLIANCEBERNSTEIN AMERICAN INCOME USD": dict(isin="", hint="American Income Portfolio S USD Acc", suffix=["EUFUND"]),
"AMUNDI BD GLOBAL AGG AUC 3D USD": dict(isin="LU1437021972", hint="Amundi Funds Global Aggregate Bond", suffix=["EUFUND"]),
"ARBROOK G10 AMERICAN EQUITIES A1 USD ACC USD": dict(isin="IE00BZ60K206", hint="Arbrook American Equities", suffix=["EUFUND"]),
"ARTISAN PTNRS GBL GLOBAL OPPORTUNITIES I USD": dict(isin="", hint="Artisan Global Opportunities", suffix=["EUFUND"]),
"BLACKROCK (LUX) SA BGF GLOBAL INFL L A2 USD": dict(isin="LU0425308086", hint="BlackRock Global Inflation Linked Bond A2", suffix=["EUFUND"]),
"BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPP A2 USD USD": dict(isin="LU0278466700", hint="BlackRock Fixed Income Global Opportunities A2", suffix=["EUFUND"]),
"BLACKROCK (LUX) SA FIXED INCOME GLOBAL OPPS D5 USD": dict(isin="LU0737136415", hint="BlackRock Fixed Income Global Opportunities D5", suffix=["EUFUND"]),
"CAPITAL CITIGROUP GLOBAL MARKETS FUNDING MEMORY COUPON USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BBVA GLOBAL QUAD INCOME USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 3 USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 4 USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 7 USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 8 USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE 9 USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY BNP PARIBAS GLOBAL INCOME LOCK IN NOTE USD": dict(isin="", hint="", suffix=[]),
"CAUSEWAY MORGAN STANLEY GLOBAL MARKETS INCOME NOTE USD": dict(isin="", hint="", suffix=[]),
"CELERITY GLOBAL BALANCED FUND IC A ACC USD": dict(isin="", hint="Celerity Global Balanced", suffix=["EUFUND"]),
"COMMERZBANK GLOBAL INDEX INCOME BUILDER 70-70 NOV 18 USD": dict(isin="", hint="", suffix=[]),
"CT MGMT AMERICAN 3U USD ACC USD": dict(isin="LU1864949380", hint="CT Lux American 3U", suffix=["EUFUND"]),
"CTMGMT LUX AMERICAN AU USD ACC USD": dict(isin="", hint="CT Lux American", suffix=["EUFUND"]),
"FINCREST GLOBAL EQUITY FUND CLASS A USD": dict(isin="", hint="FincRest Global Equity", suffix=["EUFUND"]),
"FRANKLIN TEMP GLOBAL HI YLD MDIS $ USD": dict(isin="", hint="Franklin High Yield Fund", suffix=["EUFUND"]),
"FRANKLIN TEMP GLOBAL INC A ACC USD USD": dict(isin="", hint="Templeton Global Income Fund", suffix=["EUFUND"]),
"FRANKLIN TEMPL GLOBAL FOCUS FD A DIS USD": dict(isin="", hint="Franklin Global Focus", suffix=["EUFUND"]),
"FRANKLIN TEMPLETON FRANKLIN MUT GLOBAL DVRY A CAP USD": dict(isin="", hint="Franklin Mutual Global Discovery", suffix=["EUFUND"]),
"FRANKLIN TEMPLETON GLOBAL FOCUS A ACC USD": dict(isin="", hint="Franklin Global Focus", suffix=["EUFUND"]),
"FRANKLIN TEMPLETON GLOBAL TOTAL RETURN A MDIS USD USD": dict(isin="", hint="Templeton Global Total Return", suffix=["EUFUND"]),
"FRANKLIN TEMPLETON GLOBAL TOTAL RETURN FUN A ACC USD USD": dict(isin="", hint="Templeton Global Total Return", suffix=["EUFUND"]),
"FRANKLIN TEMPLETON LATIN AMERICA A ACC USD": dict(isin="", hint="Templeton Latin America", suffix=["EUFUND"]),
"FTGF GBL BRANDYWNE GLOBAL FIXED INCOME A USD ACC USD": dict(isin="", hint="Brandywine Global Fixed Income Fund", suffix=["EUFUND"]),
"FTGF GBL W/A GLOBAL HIGH YIELD A USD ACC USD": dict(isin="IE00B1BXHP82", hint="Western Asset Global High Yield A US$ Accumulating", suffix=["EUFUND"]),
"GLOBAL X FDS GBL X FTSE ARGENT USD USD": dict(isin="ARGT", hint="Global X FTSE Argentina", suffix=["US"]),
"GLOBAL X FDS GBL X ROBOTICS & ARTIFICIAL USD": dict(isin="BOTZ", hint="Global X Robotics Artificial Intelligence", suffix=["US"]),
"GUINNESS GAM GLOBAL EQUITY INCOME INC D USD": dict(isin="", hint="Guinness Global Equity Income", suffix=["EUFUND"]),
"IDAD NATIXIS GLOBAL INDICES AC JULY 2026 USD": dict(isin="", hint="", suffix=[]),
"IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC APRIL 2026 USD": dict(isin="", hint="", suffix=[]),
"IDAD NATIXIS GLOBAL MARKETS DEFENSIVE AC DEC 2025 USD": dict(isin="", hint="", suffix=[]),
"INVESCO MANAGEMENT GLOBAL EQUITY INCOME A USD ACC NAV USD": dict(isin="LU0607513230", hint="Invesco Global Equity Income", suffix=["EUFUND"]),
"INVESCO MANAGEMENT GLOBAL SMALL CAP EQUITY A USD": dict(isin="LU1075211273", hint="Invesco Global Small Cap Equity", suffix=["EUFUND"]),
"iShares Macquarie Global Infra USD": dict(isin="IDIN", hint="iShares Global Infrastructure", suffix=["LSE", "US"]),
"JPM IF GLOBAL DIVIDEND C ACC USD": dict(isin="", hint="JPMorgan Global Dividend C acc USD", suffix=["EUFUND"]),
"JPMF A JPMF AMERICA EQUITY A USD USD": dict(isin="", hint="JPMorgan America Equity A acc USD", suffix=["EUFUND"]),
"JPMF AM GLOBAL EQUITY A DIST USD USD": dict(isin="", hint="JPMorgan Global Equity A dist USD", suffix=["EUFUND"]),
"JPMORGAN IF ASSET MGM GLOBAL BAL HGD A ACC USD USD": dict(isin="", hint="JPMorgan Global Balanced", suffix=["EUFUND"]),
"JPMORGAN IF ASSET MGM GLOBAL INCOME HEDGED A USD ACC NAV USD USD": dict(isin="", hint="JPMorgan Global Income", suffix=["EUFUND"]),
"JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS A HGD USD": dict(isin="", hint="JPMorgan Global Macro Opportunities", suffix=["EUFUND"]),
"JPMORGAN IF ASSET MGM GLOBAL MACRO OPPS C USD ACC USD": dict(isin="", hint="JPMorgan Global Macro Opportunities C", suffix=["EUFUND"]),
"JPMORGAN IF GLOBAL INCOME C DIS HDG USD": dict(isin="", hint="JPMorgan Global Income C", suffix=["EUFUND"]),
"JSS EMERGINGSAR GLOBAL A DIST USD": dict(isin="", hint="JSS Sustainable Equity Global", suffix=["EUFUND"]),
"LEVERAGE VANILLA GLOBAL BALANCED INVESTMENT ETP USD": dict(isin="", hint="", suffix=[]),
"MARIANA BBVA GLOBAL MARKETS MEMORY INCOME GENERATOR 8560 USD": dict(isin="", hint="", suffix=[]),
"MARIANA GLOBAL GROWTH KICK OUT NOTE V2 USD": dict(isin="", hint="", suffix=[]),
"MARIANA INVESTEC GLOBAL INDEX INCOME BUILDER 65 USD": dict(isin="", hint="", suffix=[]),
"MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL EQUITY FUND A USD ACCUMULATION USD": dict(isin="LU2495477510", hint="Montlake Quilter Cheviot International Equity", suffix=["EUFUND"]),
"MONTLAKE UCITS PLATFORM ICAV - QUILTER CHEVIOT INTERNATIONAL GROWTH FUND A USD ACCUMULATION USD": dict(isin="LU2495477510", hint="Montlake Quilter Cheviot International Growth", suffix=["EUFUND"]),
"NATIXIS INTL (LUX) HARRIS ASSOCS GLOBAL EQUITY I ACC USD": dict(isin="", hint="Harris Associates Global Equity", suffix=["EUFUND"]),
"NEUBERGER BERMN II GLOBAL SNR FTG RTE INC I US USD": dict(isin="", hint="Neuberger Berman Global Senior Floating Rate Income", suffix=["EUFUND"]),
"NG MORNINGSTAR GLOBAL DEFENSIV A USD ACC USD": dict(isin="", hint="Next Generation Morningstar Global Defensive", suffix=["EUFUND"]),
"NG MORNINGSTAR GLOBAL GROWTH A USD ACC USD": dict(isin="", hint="Next Generation Morningstar Global Growth", suffix=["EUFUND"]),
"PICTET FUNDS GLOBAL MEGATREND SEL I USD ACC USD": dict(isin="LU2518694729", hint="Pictet Global Megatrend Selection I USD", suffix=["EUFUND"]),
"PICTET FUNDS GLOBAL MEGATREND SELECTION P ACC USD USD": dict(isin="LU0175074193", hint="Pictet Global Megatrend Selection P USD", suffix=["EUFUND"]),
"PIMCOG GLOBAL ADVIS INCOME PU INC USD": dict(isin="", hint="PIMCO GIS Income Fund", suffix=["EUFUND"]),
"PROSPER FDS SICAV GLOBAL MACRO I USD": dict(isin="", hint="Prosper Funds SICAV Global Macro", suffix=["EUFUND"]),
"RUSSELL OLD MUTUAL VALUE GLOBAL EQUITY E ACC USD": dict(isin="IE00BYW8MG91", hint="Russell Old Mutual Value Global Equity", suffix=["EUFUND"]),
"RUSSELL OPENWORLD GLOBAL HIGH DIVIDEND EQUITY I USD": dict(isin="", hint="OpenWorld Global High Dividend Equity", suffix=["EUFUND"]),
"SCHRODER INV MGMT QEP GLOBAL ACTIVE VAL A ACC USD USD": dict(isin="", hint="Schroder QEP Global Active Value", suffix=["EUFUND"]),
"THREADNEEDLE LATIN AMERICAN NAV ACC USD": dict(isin="GB0002977949", hint="Threadneedle Latin American", suffix=["EUFUND", "GB", "LSE"]),
"VONTOBEL MGMT SA MIV GLOBAL MEDTECH P3 USD R USD": dict(isin="", hint="MIV Global Medtech P3 USD", suffix=["EUFUND"]),
"VULCAN GLOBAL VALU VALUE EQUITY USD II INC NAV USD": dict(isin="IE00BC7GWL98", hint="Vulcan Value Equity", suffix=["EUFUND"]),
}

def get(url, tries=2):
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429 or "limit" in body.lower() or "daily" in body.lower():
                return e.code, body
            return e.code, body
        except Exception as e:
            time.sleep(2)
    return 0, "network error"

def eod_pull(symbol):
    for _ in range(len(KEYS) + 1):
        k = pick_key()
        if k is None:
            return 429, "all keys exhausted"
        _used[k] += 1
        u = f"https://eodhd.com/api/eod/{symbol}?api_token={k}&fmt=json"
        st, b = get(u)
        if st in (429, 403) or "limit" in b.lower() or "daily" in b.lower():
            mark_exhausted(k)
            continue
        return st, b
    return 429, "all keys exhausted"

def eo_search(q):
    for _ in range(len(KEYS) + 1):
        k = pick_key()
        if k is None:
            return 429, []
        _used[k] += 1
        u = f"https://eodhd.com/api/search/{urllib.parse.quote(q)}?api_token={k}&fmt=json"
        st, b = get(u)
        if st in (429, 403) or "limit" in b.lower() or "daily" in b.lower():
            mark_exhausted(k)
            continue
        if st != 200:
            return st, []
        try:
            return st, json.loads(b)
        except Exception:
            return st, []
    return 429, []

def pick_best(hits, hint, want_usd=True):
    """从 EODHD search 结果里挑最像的基金条目。返回 (code, exchange, name) 或 None。"""
    hint_tokens = set(re.findall(r"[a-z0-9]+", hint.lower()))
    scored = []
    for h in hits:
        code = h.get("Code") or ""
        name = h.get("Name") or ""
        typ = h.get("Type") or ""
        exch = h.get("Exchange") or ""
        if not (re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9,10}", code) or code.startswith("0P")):
            continue
        if typ not in ("FUND", "Mutual Fund", "ETF"):
            continue
        nm_tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
        inter = len(hint_tokens & nm_tokens)
        score = inter - 0.3 * abs(len(hint_tokens) - len(nm_tokens))
        if "usd" in name.lower():
            score += 0.5
        scored.append((score, code, exch, name))
    scored.sort(key=lambda x: -x[0])
    if scored and scored[0][0] >= 1.0:
        return scored[0][1], scored[0][2], scored[0][3]
    return None

def save_panel(name, rows):
    safe = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    p = OUT_DIR / (safe + ".csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Open", "High", "Low", "Close", "Adjusted_close"])
        for r in rows:
            w.writerow([r["date"], r.get("open"), r.get("high"), r.get("low"), r["close"], r.get("adjusted_close")])
    return p

def log_write(rows):
    with open(LOG_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "status", "symbol", "rows", "first", "last", "note", "ts"])
        w.writeheader(); w.writerows(rows)

def main():
    args = sys.argv[1:]
    max_calls = 18
    only = None
    if "--max-calls" in args:
        max_calls = int(args[args.index("--max-calls") + 1])
    if "--only" in args:
        only = args[args.index("--only") + 1]

    funds = [r for r in csv.DictReader(open(BASE / "01_数据" / "eip_manual_download.csv", encoding="utf-8-sig")) if r["kind"] == "基金"]
    if only:
        funds = [r for r in funds if only in r["name"]]

    # 已有日志
    log = {}
    if LOG_CSV.exists():
        for r in csv.DictReader(open(LOG_CSV, encoding="utf-8-sig")):
            log[r["name"]] = r

    calls = 0
    new_log = []
    for r in funds:
        nm = r["name"]
        m = MAP.get(nm, {})
        isin, hint, suffix = m.get("isin", ""), m.get("hint", ""), m.get("suffix", [])
        if not suffix:
            new_log.append(dict(name=nm, status="SKIP-结构件", symbol="", rows="", first="", last="", note="结构化/ETP，跳过", ts=time.strftime("%Y-%m-%d %H:%M")))
            continue
        if nm in log and log[nm].get("status") == "OK":
            new_log.append(log[nm]); continue
        if calls >= max_calls:
            new_log.append(dict(name=nm, status="PENDING", symbol="", rows="", first="", last="", note="今日额度用尽，明天续跑", ts=time.strftime("%Y-%m-%d %H:%M")))
            continue

        done = False; status = ""; symbol = ""; note = ""
        if isin:
            for sfx in suffix:
                calls += 1
                st, b = eod_pull(f"{isin}.{sfx}")
                if st == 200 and b.strip().startswith("["):
                    rows = json.loads(b)
                    if rows:
                        save_panel(nm, rows)
                        new_log.append(dict(name=nm, status="OK", symbol=f"{isin}.{sfx}", rows=len(rows), first=rows[0]["date"], last=rows[-1]["date"], note="", ts=time.strftime("%Y-%m-%d %H:%M")))
                        done = True; break
                elif "limit" in b.lower() or st == 429:
                    new_log.append(dict(name=nm, status="PENDING", symbol="", rows="", first="", last="", note="额度用尽", ts=time.strftime("%Y-%m-%d %H:%M")))
                    calls = max_calls; break
            if done: continue
            if calls >= max_calls: continue

        if hint and calls < max_calls:
            calls += 1
            st, hits = eo_search(hint)
            if "limit" in str(hits).lower() or st == 429:
                new_log.append(dict(name=nm, status="PENDING", symbol="", rows="", first="", last="", note="额度用尽", ts=time.strftime("%Y-%m-%d %H:%M")))
                calls = max_calls; continue
            best = pick_best(hits, hint)
            if best:
                code, exch, bname = best
                new_note = f"search->{bname}"
                for sfx in [exch] + [s for s in suffix if s != exch]:
                    if calls >= max_calls: break
                    calls += 1
                    st, b = eod_pull(f"{code}.{sfx}")
                    if st == 200 and b.strip().startswith("["):
                        rows = json.loads(b)
                        if rows:
                            save_panel(nm, rows)
                            new_log.append(dict(name=nm, status="OK", symbol=f"{code}.{sfx}", rows=len(rows), first=rows[0]["date"], last=rows[-1]["date"], note=new_note, ts=time.strftime("%Y-%m-%d %H:%M")))
                            done = True; break
                    elif "limit" in b.lower() or st == 429:
                        calls = max_calls; break
                if done: continue
                if calls >= max_calls: continue
            if not done:
                new_log.append(dict(name=nm, status="NOT_FOUND", symbol="", rows="", first="", last="", note=f"search '{hint}' 无命中", ts=time.strftime("%Y-%m-%d %H:%M")))
                continue
        if not done:
            new_log.append(dict(name=nm, status="NOT_FOUND", symbol="", rows="", first="", last="", note="无 ISIN 且无搜索词", ts=time.strftime("%Y-%m-%d %H:%M")))

    # 合并旧日志里本轮没碰到的
    merged = {r["name"]: r for r in new_log}
    for nm0, r0 in log.items():
        if nm0 not in merged:
            merged[nm0] = r0
    log_write([merged[k] for k in sorted(merged)])
    print("calls used this run:", calls)
    from collections import Counter
    print("status:", dict(Counter(x["status"] for x in new_log)))
    print("log:", LOG_CSV)

if __name__ == "__main__":
    main()