"""Build a two-fund m30 sample in the new auditable layout."""

from __future__ import annotations

import pathlib
import json
import sys

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import config
import scan_v4_thresholds as s4


STAT_NAMES = ["Hit Ratio", "Up Count", "Down Count", "Average", "Max", "Min", "Count", "Std", "Sum"]
FUNDS = ["UOPIX", "ULPIX"]
WINDOW_DAYS = 60

thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_fill = PatternFill("solid", fgColor="F2F2F2")
title_font = Font(name="Arial", size=14, bold=True)
head_font = Font(name="Arial", size=9, bold=True)
body_font = Font(name="Arial", size=9)


def sign_expr(s: str, col: str, row: int) -> str:
    if s == "up":
        return f"{col}{row}>0"
    return f"{col}{row}<0"


def etf_cond_expr(tokens: list[str], row: int, colmap: dict[str, str]) -> str:
    etf = tokens[0]
    suffix = "_".join(tokens[1:])
    col = colmap[etf]
    if suffix == "up":
        return f"{col}{row}>0"
    if suffix == "down":
        return f"{col}{row}<0"
    if suffix == "big_up":
        return f"{col}{row}>=1"
    if suffix == "big_down":
        return f"{col}{row}<=-1"
    if suffix == "gt2":
        return f"{col}{row}>2"
    if suffix == "lt-2":
        return f"{col}{row}<-2"
    if suffix.startswith("bin_"):
        band = suffix[4:]
        if band == "gt2":
            return f"{col}{row}>2"
        if band == "lt-2":
            return f"{col}{row}<-2"
        lo, hi = (float(x) for x in band.split("_"))
        return f"AND({col}{row}>{lo},{col}{row}<={hi})"
    raise ValueError(suffix)


def ext_cond_expr(part: str, row: int, colmap: dict[str, str]) -> str:
    for safe, col_name in s4_load_ext_cols().items():
        prefix = f"ext_{safe}_"
        if part.startswith(prefix):
            op = part[len(prefix):]
            col = colmap[col_name]
            if op == "up":
                return f"{col}{row}>0"
            if op == "down":
                return f"{col}{row}<0"
            threshold = float(op[2:].replace("_", "."))
            if op.startswith("ge"):
                return f"{col}{row}>={threshold}"
            return f"{col}{row}<={threshold}"
    raise ValueError(part)


def self_cond_expr(suffix: str, fund_col: str, row: int) -> str:
    if suffix == "up":
        return f"{fund_col}{row}>0"
    if suffix == "down":
        return f"{fund_col}{row}<0"
    if suffix == "big_up":
        return f"{fund_col}{row}>=2"
    if suffix == "big_down":
        return f"{fund_col}{row}<=-2"
    if suffix in ("3up", "3down", "5up", "5down"):
        n = int(suffix[0])
        sign = ">" if suffix.endswith("up") else "<"
        parts = [f"{fund_col}{row - k}{sign}0" for k in range(n)]
        return "AND(" + ",".join(parts) + ")"
    raise ValueError(suffix)


def part_expr(part: str, ticker: str, row: int, colmap: dict[str, str], fund_col: str) -> str:
    if part.startswith("ext_"):
        return ext_cond_expr(part, row, colmap)
    if part.startswith("self_"):
        return self_cond_expr(part.removeprefix("self_"), fund_col, row)
    tokens = part.split("_")
    return etf_cond_expr(tokens, row, colmap)


def condition_expr(condition: str, ticker: str, row: int, colmap: dict[str, str], fund_col: str) -> str:
    if condition.startswith("combo_"):
        parts = condition[len("combo_"):].split("__")
        return "AND(" + ",".join(part_expr(p, ticker, row, colmap, fund_col) for p in parts) + ")"
    if condition.startswith("ext_") or condition.startswith("self_"):
        return part_expr(condition, ticker, row, colmap, fund_col)
    tokens = condition.split("_")
    if len(tokens) == 6 and tokens[0] in colmap and tokens[2] in colmap and tokens[4] in colmap:
        return "AND(" + ",".join(sign_expr(tokens[i + 1], colmap[tokens[i]], row) for i in (0, 2, 4)) + ")"
    if len(tokens) == 4 and tokens[0] in colmap and tokens[2] in colmap:
        return "AND(" + sign_expr(tokens[1], colmap[tokens[0]], row) + "," + sign_expr(tokens[3], colmap[tokens[2]], row) + ")"
    return etf_cond_expr(tokens, row, colmap)


def etf_label(tokens: list[str]) -> str:
    etf = tokens[0]
    suffix = "_".join(tokens[1:])
    if suffix == "up":
        return f"{etf}>0"
    if suffix == "down":
        return f"{etf}<0"
    if suffix == "big_up":
        return f"{etf}>=1%"
    if suffix == "big_down":
        return f"{etf}<=-1%"
    if suffix == "gt2":
        return f"{etf}>2%"
    if suffix == "lt-2":
        return f"{etf}<-2%"
    return f"{etf} {suffix}"


def ext_label(part: str) -> str:
    short = {
        "VIX_Close": "VIX收盘",
        "VIX_Chg%": "VIX",
        "VIX_5dChg": "VIX5d",
        "VIX_20dVol": "VIX20d",
        "TNX_Yield": "TNX",
        "TNX_ChgBp": "TNXbp",
        "CreditSpread": "信用利差",
        "JNKSpread": "高收益利差",
        "StkBonCorr": "股债相关",
        "USDGoldRatio": "美元/黄金",
        "SectRotation": "板块轮动",
        "VIX_TNX_Ratio": "VIX/TNX",
        "YldCurveProxy": "收益率曲线",
    }
    for safe, col_name in s4_load_ext_cols().items():
        prefix = f"ext_{safe}_"
        if part.startswith(prefix):
            op = part[len(prefix):]
            name = short.get(col_name, col_name)
            if op == "up":
                return f"{name}>0"
            if op == "down":
                return f"{name}<0"
            threshold = float(op[2:].replace("_", "."))
            if op.startswith("ge"):
                return f"{name}>={threshold}%"
            return f"{name}<={threshold}%"
    return part


def self_label(suffix: str) -> str:
    if suffix == "up":
        return "基金>0"
    if suffix == "down":
        return "基金<0"
    if suffix == "big_up":
        return "基金>=2%"
    if suffix == "big_down":
        return "基金<=-2%"
    if suffix == "3up":
        return "基金连涨3日"
    if suffix == "3down":
        return "基金连跌3日"
    if suffix == "5up":
        return "基金连涨5日"
    if suffix == "5down":
        return "基金连跌5日"
    return suffix


def condition_label(condition: str) -> str:
    if condition.startswith("combo_"):
        parts = condition[len("combo_"):].split("__")
        labels = []
        for p in parts:
            if p.startswith("ext_"):
                labels.append(ext_label(p))
            elif p.startswith("self_"):
                labels.append(self_label(p.removeprefix("self_")))
            else:
                labels.append(etf_label(p.split("_")))
        return " 且 ".join(labels) + "，买基金第二天"
    if condition.startswith("ext_"):
        return ext_label(condition) + "，买基金第二天"
    if condition.startswith("self_"):
        return self_label(condition.removeprefix("self_")) + "，买基金第二天"
    tokens = condition.split("_")
    if len(tokens) == 6:
        labels = [etf_label([tokens[0], tokens[1]]), etf_label([tokens[2], tokens[3]]), etf_label([tokens[4], tokens[5]])]
        return " 且 ".join(labels) + "，买基金第二天"
    if len(tokens) == 4:
        labels = [etf_label([tokens[0], tokens[1]]), etf_label([tokens[2], tokens[3]])]
        return " 且 ".join(labels) + "，买基金第二天"
    return etf_label(tokens) + "，买基金第二天"


def s4_load_ext_cols():
    import scan_v4_conditions as sc
    return sc.EXTERNAL_COLS


def load_fund_adj(ticker: str) -> dict:
    p = config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始" / "profunds" / "adj_close_nasdaq" / f"{ticker}.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    rows = data["data"]["tradesTable"]["rows"]
    out = {}
    for r in rows:
        d = pd.to_datetime(r["date"], format="%m/%d/%Y")
        out[d] = float(r["adjustedClose"])
    return out


def load_etf_adj(ticker: str) -> dict:
    if ticker == "XLC":
        p = config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始" / "etfs_extended" / "XLC.csv"
    else:
        p = config.RESULT_ROOT / "最新成果" / "数据" / "数据_原始" / "etfs" / f"{ticker}_historical.csv"
    df = pd.read_csv(p)
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    return dict(zip(df["Date"], df["Adj Close"]))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    master = s4.load_master()
    fund_panel = pd.read_csv(config.FUND_PANEL).rename(columns={"date": "Date"})
    fund_panel["Date"] = pd.to_datetime(fund_panel["Date"])
    dates_all = sorted(pd.to_datetime(master["Date"]), reverse=True)[:WINDOW_DAYS]
    dates_all = sorted(dates_all, reverse=True)

    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv", keep_default_na=False)
    strat = {t: mapping[mapping["ticker"] == t].sort_values("strategy_no") for t in FUNDS}
    name_map = pd.read_csv(config.MIDDLE / "通用" / "文件" / "基金名称映射.csv", keep_default_na=False)
    name_by_ticker = dict(zip(name_map["ticker"], name_map["name"]))
    fund_label = {t: f"{name_by_ticker.get(t, t)}（{t}）" for t in FUNDS}

    etf_cols_used = ["EEM", "GLD", "HYG", "TIP", "XLF", "FXY", "GDX", "XLC"]
    ext_cols_used = ["VIX_Chg%"]
    base_headers = []
    for t in FUNDS:
        base_headers += [f"{fund_label[t]} Adj Close", f"{fund_label[t]}回报"]
    for e in etf_cols_used:
        base_headers += [f"{e} Adj Close", f"{e}回报"]
    base_headers += ext_cols_used

    col_idx = 2
    fund_price_col = {}
    fund_return_col = {}
    for t in FUNDS:
        fund_price_col[t] = get_column_letter(col_idx); col_idx += 1
        fund_return_col[t] = get_column_letter(col_idx); col_idx += 1
    etf_price_col = {}
    etf_return_col = {}
    for e in etf_cols_used:
        etf_price_col[e] = get_column_letter(col_idx); col_idx += 1
        etf_return_col[e] = get_column_letter(col_idx); col_idx += 1
    ext_col = {}
    for e in ext_cols_used:
        ext_col[e] = get_column_letter(col_idx); col_idx += 1
    colmap = {**fund_return_col, **etf_return_col, **ext_col}

    wb = Workbook()
    ws_note = wb.active
    ws_note.title = "说明"
    ws_note["A1"] = "两基金 m30 新版式示例"
    ws_note["A1"].font = title_font
    for i, line in enumerate(
        [
            "用途：审批新版式，确认后再全量生成 m30。",
            "版式：最左侧为基础数据，每支基金前为单独策略列，最后一列为合并效果。",
            "最左侧先放原始 Adj Close，旁边回报率列用 Excel 公式从 Adj Close 计算。",
            "策略列/合并列引用回报率列计算，全部为 Excel 公式。",
            "日期格式：YYYY/MM/DD，按公司格式降序。",
            "策略名写清阈值，并统一标注“买基金第二天”。",
            "示例基金：" + "、".join(fund_label[t] for t in FUNDS) + "，最近 60 个交易日。",
        ],
        start=3,
    ):
        ws_note.cell(row=i, column=1, value=line)
    ws_note.column_dimensions["A"].width = 110

    ws = wb.create_sheet("数据")
    n_base = len(base_headers)
    per_fund = {t: list(strat[t]["condition"]) for t in FUNDS}
    headers = ["日期"] + base_headers
    for t in FUNDS:
        for c in per_fund[t]:
            headers.append(condition_label(c))
        headers.append(f"{fund_label[t]}合并效果")
    n_cols = len(headers)

    ws.append([])
    for i, label in enumerate(STAT_NAMES, start=2):
        ws.cell(row=i, column=1, value=label)
    ws.append([])
    ws.append([])
    ws.append(headers)
    ds = 14
    de = ds + len(dates_all) - 1

    for c_idx in range(2, n_cols + 1):
        col = get_column_letter(c_idx)
        ws[f"{col}2"] = f"={col}3/({col}3+{col}4)"
        ws[f"{col}3"] = f'=COUNTIF({col}{ds}:{col}{de},">0")'
        ws[f"{col}4"] = f'=COUNTIF({col}{ds}:{col}{de},"<0")'
        ws[f"{col}5"] = f"=AVERAGE({col}{ds}:{col}{de})"
        ws[f"{col}6"] = f"=MAX({col}{ds}:{col}{de})"
        ws[f"{col}7"] = f"=MIN({col}{ds}:{col}{de})"
        ws[f"{col}8"] = f"=COUNT({col}{ds}:{col}{de})"
        ws[f"{col}9"] = f"=STDEV({col}{ds}:{col}{de})"
        ws[f"{col}10"] = f"=SUM({col}{ds}:{col}{de})"

    fund_adj = {t: load_fund_adj(t) for t in FUNDS}
    etf_adj = {e: load_etf_adj(e) for e in etf_cols_used}
    ext_val = {e: dict(zip(pd.to_datetime(master["Date"]), master[e])) for e in ext_cols_used}

    # column indices of merged columns
    merged_idx = {}
    cur = 2 + n_base
    for t in FUNDS:
        cur += len(per_fund[t])
        merged_idx[t] = cur
        cur += 1
    strat_cols = {}
    cur = 2 + n_base
    for t in FUNDS:
        cols = []
        for _ in per_fund[t]:
            cols.append(cur)
            cur += 1
        strat_cols[t] = cols
        cur += 1  # merged

    weights = {
        "UOPIX": [0.549579, 0.299732, 0.323835],
        "ULPIX": [0.408167, 0.318680, 0.510996],
    }

    for i, d in enumerate(dates_all):
        r = ds + i
        row = [d.strftime("%Y/%m/%d")]
        for t in FUNDS:
            row.append(round(fund_adj[t].get(d, float("nan")), 4))
        for e in etf_cols_used:
            row.append(round(etf_adj[e].get(d, float("nan")), 4))
        for e in ext_cols_used:
            row.append(round(ext_val[e].get(d, float("nan")), 4))
        ws.append(row)
        # return formulas from Adj Close (same-day return = today / previous trading day - 1)
        price_cols = [fund_price_col[t] for t in FUNDS] + [etf_price_col[e] for e in etf_cols_used]
        ret_cols = [fund_return_col[t] for t in FUNDS] + [etf_return_col[e] for e in etf_cols_used]
        for pcol, rcol in zip(price_cols, ret_cols):
            if i < len(dates_all) - 1:
                ws[f"{rcol}{r}"] = (
                    f"=IF(AND(ISNUMBER({pcol}{r}),ISNUMBER({pcol}{r + 1})),"
                    f"({pcol}{r}/{pcol}{r + 1}-1)*100,\"\")"
                )
            else:
                ws[f"{rcol}{r}"] = ""
        # strategy formulas
        for t in FUNDS:
            fund_col = colmap[t]
            for c_idx, condition in zip(strat_cols[t], per_fund[t]):
                col = get_column_letter(c_idx)
                if i == 0:
                    ws.cell(row=r, column=c_idx, value="")
                else:
                    cond = condition_expr(condition, t, r, colmap, fund_col)
                    ws.cell(row=r, column=c_idx, value=f"=IF({cond},{fund_col}{r - 1},\"\")")
            # merged formula
            m_col = get_column_letter(merged_idx[t])
            cols = [get_column_letter(c) for c in strat_cols[t]]
            ws_weights = weights[t]
            n = len(cols)
            nested = ""
            for j in range(n):
                col = cols[j]
                others = [k for k in range(n) if k != j]
                max_expr = "MAX(" + ",".join(
                    f"IF(ISNUMBER({cols[k]}{r}),{ws_weights[k]},-1)" for k in others
                ) + ")"
                cmp = ">=" if j == 0 else ">"
                cond = f"AND(ISNUMBER({col}{r}),{ws_weights[j]}{cmp}{max_expr})"
                nested += f"IF({cond},{col}{r},"
            nested += "\"\""
            nested += ")" * n
            ws.cell(row=r, column=merged_idx[t], value=f"={nested}")

    for r in range(2, 11):
        ws.cell(row=r, column=1).font = head_font
        for c in range(2, n_cols + 1):
            ws.cell(row=r, column=c).font = body_font
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=13, column=c)
        cell.font = head_font
        cell.border = border
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for r in range(ds, de + 1):
        for c in range(1, n_cols + 1):
            ws.cell(row=r, column=c).border = border
            ws.cell(row=r, column=c).font = body_font
    ws.column_dimensions["A"].width = 12
    for c in range(2, n_cols + 1):
        ws.column_dimensions[get_column_letter(c)].width = 16
    ws.freeze_panes = "B14"

    out_dir = config.RESULT_ROOT / "示例审批"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "两基金_m30新版式示例_AdjClose公式版.xlsx"
    wb.save(out_path)
    print("saved:", out_path)
    print("cols:", n_cols, "data rows:", len(dates_all))


if __name__ == "__main__":
    main()
