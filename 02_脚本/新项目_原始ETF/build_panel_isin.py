# -*- coding: utf-8 -*-
"""建立 251 支 ISIN 基金面板：Date + 251 基金列(小数回报) + 19 ETF 列(百分数回报)。"""
import pathlib, sys, io, csv
import pandas as pd

BASE = pathlib.Path(r"C:\Users\vanessacen\Desktop\新基金预测")
D = BASE / "01_数据"
ETF_PANEL = D / "event_study_inputs" / "panel_etf_returns_adj_v2.csv"
CLEANED = D / "新项目_processed" / "eip_cleaned_isin"
PANEL = D / "新项目_processed" / "eip_panel_251etf.csv"
ORIGINAL19 = ["SPY","QQQ","IWM","TLT","TIP","EEM","LQD","HYG","UUP","SLV","JNK","GLD","GDX","XLV","XLU","XLE","XLF","XLK","FXY"]
FUND_RETURN_CLIP = 0.5

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(io.open(D / "eip_master_status.csv", encoding="utf-8-sig")))
    isins = sorted(r["isin"] for r in rows if r["status"] == "有数据-确认")
    etf = pd.read_csv(ETF_PANEL)
    etf["Date"] = pd.to_datetime(etf["Date"]).dt.strftime("%Y-%m-%d")
    etf = etf.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)
    panel = etf.copy()
    ok, short, missing = 0, [], []
    for isin in isins:
        fp = CLEANED / f"{isin}.csv"
        if not fp.exists():
            missing.append(isin); continue
        df = pd.read_csv(fp)
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df = df.dropna(subset=["Adj Close"]).drop_duplicates("Date", keep="last").sort_values("Date").reset_index(drop=True)
        if len(df) < 120:
            short.append(isin); continue
        ret = df["Adj Close"].pct_change().clip(-FUND_RETURN_CLIP, FUND_RETURN_CLIP)
        s = pd.DataFrame({"Date": df["Date"], isin: ret})
        panel = panel.merge(s, on="Date", how="left")
        ok += 1
    panel = panel.sort_values("Date").reset_index(drop=True)
    fund_cols = [c for c in panel.columns if c not in {"Date"} | set(ORIGINAL19)]
    print("panel rows:", len(panel), "range:", panel["Date"].iloc[0], "->", panel["Date"].iloc[-1])
    print("fund cols:", len(fund_cols), "etf cols:", len([c for c in ORIGINAL19 if c in panel.columns]))
    print("fund NaN cells:", int(panel[fund_cols].isna().sum().sum()))
    # per-fund non-null count
    nn = panel[fund_cols].notna().sum()
    print("funds with >=220 non-null:", int((nn >= 220).sum()), " >=1000:", int((nn >= 1000).sum()))
    print("min non-null:", int(nn.min()), "max:", int(nn.max()))
    panel.to_csv(PANEL, index=False, encoding="utf-8-sig")
    print("saved:", PANEL)
    if short: print("short:", len(short), short[:5])
    if missing: print("missing:", len(missing), missing[:5])

if __name__ == "__main__":
    main()