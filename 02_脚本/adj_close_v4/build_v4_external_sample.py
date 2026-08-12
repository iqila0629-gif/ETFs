"""Build a small sample showing the new external-data layout."""

from __future__ import annotations

import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import config
import build_v4_m30_newformat_sample as sample


ETF_ALL = ["SPY", "TLT", "HYG", "JNK", "UUP", "GLD", "XLK", "XLF", "TIP"]
DATES = [
    "2026-08-07", "2026-08-06", "2026-08-05",
    "2026-08-04", "2026-08-03", "2026-07-31", "2026-07-30", "2026-07-29",
    "2026-07-28", "2026-07-27", "2026-07-24", "2026-07-23", "2026-07-22",
    "2026-07-21", "2026-07-20", "2026-07-17", "2026-07-16", "2026-07-15",
    "2026-07-14", "2026-07-13", "2026-07-10", "2026-07-09", "2026-07-08",
    "2026-07-07", "2026-07-06",
]

def load_external_ohlc() -> dict[str, dict[pd.Timestamp, dict[str, float]]]:
    df = pd.read_csv(config.EXTERNAL_DAILY, parse_dates=["Date"]).set_index("Date")
    result: dict[str, dict[pd.Timestamp, dict[str, float]]] = {}
    for name, close_col in (("VIX", "VIX_Close"), ("TNX", "TNX_Yield")):
        result[name] = {}
        for date, row in df.iterrows():
            vals = {
                "open": row[f"{name}_Open"],
                "high": row[f"{name}_High"],
                "low": row[f"{name}_Low"],
                "close": row[close_col],
            }
            if any(pd.isna(v) for v in vals.values()):
                continue
            result[name][date] = vals
    return result

thin = Side(style="thin", color="BFBFBF")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_fill = PatternFill("solid", fgColor="F2F2F2")
head_font = Font(name="Arial", size=9, bold=True)
body_font = Font(name="Arial", size=9)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    wb = Workbook()
    ws_note = wb.active
    ws_note.title = "说明"
    ws_note["A1"] = "外部数据新版式示例"
    ws_note["A1"].font = Font(name="Arial", size=14, bold=True)
    note_lines = [
        "布局说明：",
        "1. VIX/TNX 原始数据按 ETF 格式展示：第14行=名称，第15行=Open/High/Low/Close（只保留 OHLC，不展示 Adj Close/Volume）。",
        "2. VIX/TNX 回报与变化指标集中放一起，第15行直接写名称（如 VIX回报、VIX_Chg%、TNX_ChgBp），后面用空列分隔。",
        "3. 其他派生外部列：第14行=指标名称，第15行=计算公式（谁减谁），数据区为 Excel 公式。",
        "4. ETF 回报、VIX/TNX 回报、派生指标均用公式计算，回报率保留4位小数。",
    ]
    for i, line in enumerate(note_lines, start=3):
        ws_note.cell(row=i, column=1, value=line)
    ws_note.column_dimensions["A"].width = 120

    ws = wb.create_sheet("数据")
    col_idx = 2
    blank_cols: set[int] = set()

    etf_cols = {}
    etf_ohlc = {e: sample.load_etf_ohlc(e) for e in ETF_ALL}
    ext_ohlc = load_external_ohlc()
    for e in ETF_ALL:
        etf_cols[e] = {}
        for key in ("open", "high", "low", "close", "adj", "volume", "ret"):
            etf_cols[e][key] = col_idx
            col_idx += 1
        blank_cols.add(col_idx); col_idx += 1

    vix_cols = {}
    tnx_cols = {}
    for cols in (vix_cols, tnx_cols):
        for key in ("open", "high", "low", "close"):
            cols[key] = col_idx
            col_idx += 1
        blank_cols.add(col_idx); col_idx += 1

    chg_cols = {}
    for key in ("VIX回报", "VIX_Chg%", "VIX_5dChg", "VIX_20dVol", "TNX回报", "TNX_ChgBp"):
        chg_cols[key] = col_idx
        col_idx += 1
    blank_cols.add(col_idx); col_idx += 1

    derived = {
        "CreditSpread": "HYG-TLT",
        "JNKSpread": "JNK-TLT",
        "StkBonCorr": "CORREL(SPY,TLT,近20日)",
        "USDGoldRatio": "UUP-GLD",
        "SectRotation": "XLK-XLF",
        "VIX_TNX_Ratio": "VIX_close/TNX_close",
        "YldCurveProxy": "TLT-TIP",
    }
    derived_cols = {}
    for name in derived:
        derived_cols[name] = col_idx
        col_idx += 1
    n_cols = col_idx - 1

    ws.cell(row=14, column=1, value="日期")
    ws.cell(row=15, column=1, value="日期")
    for e in ETF_ALL:
        label_c = etf_cols[e]["open"] + 2
        ws.cell(row=14, column=label_c, value=e)
        for key, label in (
            ("open", "Open"), ("high", "High"), ("low", "Low"),
            ("close", "Close"), ("adj", "Adj Close"), ("volume", "Volume"),
            ("ret", "回报"),
        ):
            ws.cell(row=15, column=etf_cols[e][key], value=label)
    for name, cols in (("VIX", vix_cols), ("TNX", tnx_cols)):
        ws.cell(row=14, column=cols["open"] + 2, value=name)
        for key, label in (
            ("open", "Open"), ("high", "High"), ("low", "Low"),
            ("close", "Close"),
        ):
            ws.cell(row=15, column=cols[key], value=label)
    chg_formula = {
        "VIX_Chg%": "VIX_close/昨VIX_close-1",
        "VIX_5dChg": "VIX_close/5日前VIX_close-1",
        "VIX_20dVol": "STDEV(VIX日变化,近20日)",
        "TNX_ChgBp": "(TNX_close-昨TNX_close)*100",
    }
    for key in chg_cols:
        if key in chg_formula:
            ws.cell(row=14, column=chg_cols[key], value=key)
            ws.cell(row=15, column=chg_cols[key], value=chg_formula[key])
        else:
            ws.cell(row=15, column=chg_cols[key], value=key)
    for name, formula in derived.items():
        ws.cell(row=14, column=derived_cols[name], value=name)
        ws.cell(row=15, column=derived_cols[name], value=formula)

    ds = 16
    de = ds + len(DATES) - 1
    for i, d in enumerate(DATES):
        r = ds + i
        date = pd.Timestamp(d)
        ws.cell(row=r, column=1, value=d.replace("-", "/"))
        for e in ETF_ALL:
            rec = etf_ohlc[e].get(date, {})
            for key in ("open", "high", "low", "close", "adj", "volume"):
                v = rec.get(key)
                if v is not None:
                    ws.cell(row=r, column=etf_cols[e][key], value=v if key == "volume" else round(v, 4))
            adj = get_column_letter(etf_cols[e]["adj"])
            if i < len(DATES) - 1:
                ws.cell(row=r, column=etf_cols[e]["ret"], value=(
                    f"=IF(COUNT({adj}{r}:{adj}{r + 1})=2,"
                    f"ROUND(({adj}{r}/{adj}{r + 1}-1)*100,4),\"\")"
                ))
        for name, cols in (("VIX", vix_cols), ("TNX", tnx_cols)):
            rec = ext_ohlc[name].get(date)
            if rec:
                for key in ("open", "high", "low", "close"):
                    ws.cell(row=r, column=cols[key], value=round(rec[key], 4))

        vc = get_column_letter(vix_cols["close"])
        tc = get_column_letter(tnx_cols["close"])
        ws.cell(row=r, column=chg_cols["VIX回报"], value=(
            f"=IF(COUNT({vc}{r}:{vc}{r + 1})=2,ROUND(({vc}{r}/{vc}{r + 1}-1)*100,4),\"\")"
        ))
        ws.cell(row=r, column=chg_cols["VIX_Chg%"], value=(
            f"=IF(COUNT({vc}{r}:{vc}{r + 1})=2,ROUND(({vc}{r}/{vc}{r + 1}-1)*100,4),\"\")"
        ))
        ws.cell(row=r, column=chg_cols["TNX回报"], value=(
            f"=IF(COUNT({tc}{r}:{tc}{r + 1})=2,ROUND(({tc}{r}/{tc}{r + 1}-1)*100,4),\"\")"
        ))
        ws.cell(row=r, column=chg_cols["TNX_ChgBp"], value=(
            f"=IF(COUNT({tc}{r}:{tc}{r + 1})=2,({tc}{r}-{tc}{r + 1})*100,\"\")"
        ))
        if i + 5 < len(DATES):
            ws.cell(row=r, column=chg_cols["VIX_5dChg"], value=(
                f"=IF(COUNT({vc}{r}:{vc}{r + 5})=6,ROUND(({vc}{r}/{vc}{r + 5}-1)*100,4),\"\")"
            ))
        if i + 20 <= de:
            vchg = get_column_letter(chg_cols["VIX_Chg%"])
            ws.cell(row=r, column=chg_cols["VIX_20dVol"], value=(
                f'=IF(COUNT({vchg}{r}:{vchg}{r + 19})=20,IFERROR(ROUND(STDEV({vchg}{r}:{vchg}{r + 19}),4),""),"")'
            ))
        for name, a, b in (
            ("CreditSpread", etf_cols["HYG"]["ret"], etf_cols["TLT"]["ret"]),
            ("JNKSpread", etf_cols["JNK"]["ret"], etf_cols["TLT"]["ret"]),
            ("USDGoldRatio", etf_cols["UUP"]["ret"], etf_cols["GLD"]["ret"]),
            ("SectRotation", etf_cols["XLK"]["ret"], etf_cols["XLF"]["ret"]),
            ("YldCurveProxy", etf_cols["TLT"]["ret"], etf_cols["TIP"]["ret"]),
        ):
            a_letter = get_column_letter(a)
            b_letter = get_column_letter(b)
            ws.cell(row=r, column=derived_cols[name], value=f'=IFERROR({a_letter}{r}-{b_letter}{r},"")')
        if i + 20 <= de:
            sp = get_column_letter(etf_cols["SPY"]["ret"])
            tl = get_column_letter(etf_cols["TLT"]["ret"])
            ws.cell(row=r, column=derived_cols["StkBonCorr"], value=(
                f'=IF(COUNT({sp}{r}:{sp}{r + 19})=20,IFERROR(CORREL({sp}{r}:{sp}{r + 19},{tl}{r}:{tl}{r + 19}),""),"")'
            ))
        ws.cell(row=r, column=derived_cols["VIX_TNX_Ratio"], value=f"={vc}{r}/{tc}{r}")

    pct_cols = []
    for e in ETF_ALL:
        pct_cols.append(etf_cols[e]["ret"])
    pct_cols += [
        chg_cols["VIX回报"], chg_cols["VIX_Chg%"], chg_cols["VIX_5dChg"],
        chg_cols["VIX_20dVol"], chg_cols["TNX回报"],
    ]
    pct_cols += [
        derived_cols["CreditSpread"], derived_cols["JNKSpread"],
        derived_cols["USDGoldRatio"], derived_cols["SectRotation"],
        derived_cols["YldCurveProxy"],
    ]
    for r in range(ds, de + 1):
        for c in pct_cols:
            ws.cell(row=r, column=c).number_format = '0.0000"%"'
        ws.cell(row=r, column=chg_cols["TNX_ChgBp"]).number_format = '0.00"bp"'
        ws.cell(row=r, column=derived_cols["StkBonCorr"]).number_format = "0.0000"
        ws.cell(row=r, column=derived_cols["VIX_TNX_Ratio"]).number_format = "0.0000"

    for row in (14, 15):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=row, column=c)
            cell.font = head_font
            cell.border = border
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[14].height = 30
    ws.row_dimensions[15].height = 30
    for r in range(ds, de + 1):
        for c in range(1, n_cols + 1):
            ws.cell(row=r, column=c).border = border
            ws.cell(row=r, column=c).font = body_font
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center", vertical="center")
    ws.column_dimensions["A"].width = 12
    for c in range(2, n_cols + 1):
        ws.column_dimensions[get_column_letter(c)].width = 14
    ws.freeze_panes = "B16"
    wb.calculation.fullCalcOnLoad = True

    out_dir = config.RESULT_ROOT / "示例审批"
    out_path = out_dir / "外部数据新版式示例.xlsx"
    wb.save(out_path)
    print("saved:", out_path, "cols", n_cols, "rows", len(DATES))


if __name__ == "__main__":
    main()
