# -*- coding: utf-8 -*-
import pathlib
p = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测\02_脚本\新项目\eodhd_batch.py")
c = p.read_text(encoding="utf-8")

repl = [
# Global X Argentina -> ETF ticker ARGT.US
('"GLOBAL X FDS GBL X FTSE ARGENT USD USD": dict(isin="", hint="Global X FTSE Argentina", suffix=["EUFUND"]),',
 '"GLOBAL X FDS GBL X FTSE ARGENT USD USD": dict(isin="ARGT", hint="Global X FTSE Argentina", suffix=["US"]),'),
# Global X Robotics -> ETF ticker BOTZ.US
('"GLOBAL X FDS GBL X ROBOTICS & ARTIFICIAL USD": dict(isin="", hint="Global X Robotics Artificial Intelligence", suffix=["EUFUND"]),',
 '"GLOBAL X FDS GBL X ROBOTICS & ARTIFICIAL USD": dict(isin="BOTZ", hint="Global X Robotics Artificial Intelligence", suffix=["US"]),'),
# Brandywine hint
('"FTGF GBL BRANDYWNE GLOBAL FIXED INCOME A USD ACC USD": dict(isin="", hint="FTGF Brandywine Global Fixed Income", suffix=["EUFUND"]),',
 '"FTGF GBL BRANDYWNE GLOBAL FIXED INCOME A USD ACC USD": dict(isin="", hint="Brandywine Global Fixed Income Fund", suffix=["EUFUND"]),'),
# Guinness hint shorter
('"GUINNESS GAM GLOBAL EQUITY INCOME INC D USD": dict(isin="", hint="Guinness Global Equity Income D USD", suffix=["EUFUND"]),',
 '"GUINNESS GAM GLOBAL EQUITY INCOME INC D USD": dict(isin="", hint="Guinness Global Equity Income", suffix=["EUFUND"]),'),
# Aberdeen hint variant
('"ABERDEEN STD - NORTH AMERICAN SMALLER COMPANIES FUND I ACC USD USD": dict(isin="", hint="Aberdeen American Growth", suffix=["EUFUND"]),',
 '"ABERDEEN STD - NORTH AMERICAN SMALLER COMPANIES FUND I ACC USD USD": dict(isin="", hint="abrdn American Growth", suffix=["EUFUND"]),'),
# iShares -> ticker IDIN.LSE
('"iShares Macquarie Global Infra USD": dict(isin="", hint="iShares Global Infrastructure", suffix=["EUFUND"]),',
 '"iShares Macquarie Global Infra USD": dict(isin="IDIN", hint="iShares Global Infrastructure", suffix=["LSE", "US"]),'),
# retry NOT_FOUND each run
('if nm in log and log[nm].get("status") in ("OK", "NOT_FOUND"):',
 'if nm in log and log[nm].get("status") == "OK":'),
]
for old, new in repl:
    if old not in c:
        raise SystemExit("NOT FOUND: " + old[:80])
    c = c.replace(old, new)
p.write_text(c, encoding="utf-8")
print("patched OK")