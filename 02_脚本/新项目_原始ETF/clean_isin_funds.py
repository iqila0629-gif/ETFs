# -*- coding: utf-8 -*-
"""清洗 251 支 ISIN 基金净值（复用 v4 尖峰/断层修复逻辑）→ 01_数据/新项目_processed/eip_cleaned_isin/{ISIN}.csv"""
import pathlib, sys, io, csv
import numpy as np
import pandas as pd

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
PRICE_DIR = D / "新项目_基金价格_isin"
CLEANED = D / "新项目_processed" / "eip_cleaned_isin"
CLEANED.mkdir(parents=True, exist_ok=True)
THRESHOLD = 0.5

def fix_series(closes, dates, fund):
    closes = closes.copy()
    log = []
    while True:
        with np.errstate(invalid="ignore", divide="ignore"):
            returns = np.divide(closes[1:], closes[:-1], out=np.zeros_like(closes[:-1]), where=closes[:-1] != 0) - 1
        bad = np.where(np.abs(returns) >= THRESHOLD)[0]
        if len(bad) == 0:
            break
        i = int(bad[0])
        pre = closes[i]
        spike = closes[i+1]
        j = i + 2
        while j < len(closes) and abs(closes[j] / spike - 1) < 0.05:
            j += 1
        if j >= len(closes):
            factor = spike / pre if pre != 0 else 1.0
            closes[:i+1] = closes[:i+1] * factor
            log.append({"fund": fund, "date": dates[i+1], "type": "level_shift", "factor": float(factor)})
            continue
        ratio = closes[j] / pre if pre != 0 else 0.0
        if 0.5 <= ratio <= 1.5:
            for k in range(i+1, j):
                log.append({"fund": fund, "date": dates[k], "type": "spike", "factor": 1.0})
            closes[i+1:j] = pre
        else:
            factor = spike / pre if pre != 0 else 1.0
            closes[:i+1] = closes[:i+1] * factor
            log.append({"fund": fund, "date": dates[i+1], "type": "level_shift", "factor": float(factor)})
    return closes, log

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(io.open(D / "eip_master_status.csv", encoding="utf-8-sig")))
    isins = sorted(r["isin"] for r in rows if r["status"] == "有数据-确认")
    print("to clean:", len(isins), flush=True)
    all_log = []
    ok, fail = 0, 0
    for i, isin in enumerate(isins, 1):
        fp = PRICE_DIR / f"{isin}.csv"
        if not fp.exists():
            print(f"[{i}] MISSING {isin}", flush=True); fail += 1; continue
        df = pd.read_csv(fp)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Adj Close"]).sort_values("Date")
        df = df.drop_duplicates("Date", keep="last")
        if len(df) < 120:
            print(f"[{i}] SHORT {isin} rows={len(df)}", flush=True); fail += 1; continue
        dates = [d.strftime("%Y-%m-%d") for d in df["Date"]]
        closes = df["Adj Close"].to_numpy(dtype=float)
        cleaned, log = fix_series(closes, dates, isin)
        all_log.extend(log)
        out = pd.DataFrame({"Date": dates, "Adj Close": cleaned})
        out.to_csv(CLEANED / f"{isin}.csv", index=False, encoding="utf-8-sig")
        ok += 1
        if i % 25 == 0:
            print(f"[{i}/{len(isins)}] ok={ok} fail={fail} fixes={len(all_log)}", flush=True)
    print("cleaned OK:", ok, "fail:", fail, "fixes:", len(all_log))
    if all_log:
        pd.DataFrame(all_log).to_csv(D / "新项目_processed" / "eip_cleaning_log_isin.csv", index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    main()