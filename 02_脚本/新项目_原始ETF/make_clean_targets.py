# -*- coding: utf-8 -*-
"""Build clean target list from confirmed EIP funds (eip_confirmed.csv).

Rules (decision-complete):
  1) yahoo_type == MUTUALFUND
  2) one row per symbol (best overlap -> most history -> lexicographic name)
  3) history >= 120 trading days (max of yahoo/is-in chart-check rows; actual re-checked after download)
  4) overlap >= 0.7
  5) exclude money-market funds (name contains "MONEY"), consistent with v4

Outputs:
  - 01_数据/eip_clean_targets.csv   (clean targets, original confirmed columns + rows_ok)
  - 01_数据/eip_clean_excluded.csv  (every excluded row + reason, for review)
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[2]
DATA = BASE / "01_数据"

CONFIRMED = DATA / "eip_confirmed.csv"
YAHOO_CHK = DATA / "eip_yahoo_chart_check.csv"
ISIN_CHK = DATA / "eip_isin_chart_check.csv"
OUT_TARGETS = DATA / "eip_clean_targets.csv"
OUT_EXCLUDED = DATA / "eip_clean_excluded.csv"

MIN_ROWS = 120
MIN_OVERLAP = 0.7
MONEY_KEYWORDS = ("MONEY",)


def chart_rows(name: str, ychk: pd.DataFrame, ichk: pd.DataFrame) -> float:
    vals: list[float] = []
    y = ychk.loc[ychk["name"] == name]
    if len(y):
        v = y.iloc[0].get("rows_ok")
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            pass
    i = ichk.loc[ichk["name"] == name]
    if len(i):
        v = i.iloc[0].get("rows")
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            pass
    finite = [v for v in vals if v == v]  # drop NaN before max()
    return max(finite) if finite else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conf = pd.read_csv(CONFIRMED, encoding="utf-8")
    ychk = pd.read_csv(YAHOO_CHK, encoding="utf-8")
    ichk = pd.read_csv(ISIN_CHK, encoding="utf-8")

    df = conf.copy()
    df["rows_ok"] = df["name"].apply(lambda n: chart_rows(n, ychk, ichk))

    excluded: list[dict] = []

    def exclude(row: pd.Series, reason: str) -> None:
        excluded.append({
            "name": row["name"],
            "category": row["category"],
            "symbol": row.get("symbol"),
            "overlap": row.get("overlap"),
            "rows_ok": row.get("rows_ok"),
            "reason": reason,
        })

    # Rule 1: mutual funds only
    mutual = df[df["yahoo_type"] == "MUTUALFUND"].copy()
    for _, r in df[df["yahoo_type"] != "MUTUALFUND"].iterrows():
        exclude(r, f"非MUTUALFUND({r['yahoo_type']})")

    # Rule 2: one row per symbol, keep best (overlap desc, rows desc, name asc)
    best = (
        mutual.sort_values(["symbol", "overlap", "rows_ok", "name"],
                           ascending=[True, False, False, True])
        .drop_duplicates("symbol", keep="first")
    )
    for _, r in mutual.loc[~mutual["name"].isin(best["name"])].iterrows():
        exclude(r, "同symbol多条只保留最优一条")

    # Rule 3: history >= MIN_ROWS
    rows_keep = best[best["rows_ok"] >= MIN_ROWS]
    for _, r in best[best["rows_ok"] < MIN_ROWS].iterrows():
        exclude(r, f"历史行数不足({r['rows_ok']}<{MIN_ROWS})")

    # Rule 4: overlap >= MIN_OVERLAP
    ov_keep = rows_keep[pd.to_numeric(rows_keep["overlap"], errors="coerce") >= MIN_OVERLAP]
    for _, r in rows_keep[pd.to_numeric(rows_keep["overlap"], errors="coerce") < MIN_OVERLAP].iterrows():
        exclude(r, f"名称匹配度过低({r['overlap']}<{MIN_OVERLAP})")

    # Rule 5: money-market exclusion
    is_money = ov_keep["name"].str.upper().str.contains("|".join(MONEY_KEYWORDS), na=False)
    clean = ov_keep[~is_money]
    for _, r in ov_keep[is_money].iterrows():
        exclude(r, "货币基金(MONEY)排除")

    clean = clean.sort_values(["category", "name"]).reset_index(drop=True)
    excl = pd.DataFrame(excluded)

    cols = ["name", "category", "source", "symbol", "isin", "ref_name", "yahoo_name",
            "overlap", "currency_ok", "yahoo_currency", "yahoo_type", "verdict",
            "recommendation", "rows_ok"]
    clean[cols].to_csv(OUT_TARGETS, index=False, encoding="utf-8-sig")
    excl.to_csv(OUT_EXCLUDED, index=False, encoding="utf-8-sig")

    print(f"confirmed total       : {len(df)}")
    print(f"clean targets         : {len(clean)}  by_cat={dict(clean['category'].value_counts())}")
    print(f"excluded              : {len(excl)}")
    print(f"reason counts         : {dict(excl['reason'].value_counts())}")
    print(f"saved: {OUT_TARGETS}")
    print(f"saved: {OUT_EXCLUDED}")


if __name__ == "__main__":
    main()