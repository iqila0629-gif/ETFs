"""Build aligned daily return panels from the combined NAV / ETF tables."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "processed_returns"
OUT_DIR = ROOT / "analysis_results" / "event_study"
NAV_FILE = DATA_DIR / "combined_profunds_nav.csv"
ETF_FILE = DATA_DIR / "combined_etf_returns.csv"
FUND_PANEL = OUT_DIR / "panel_fund_returns.csv"
ETF_PANEL = OUT_DIR / "panel_etf_returns.csv"
QUALITY_REPORT = OUT_DIR / "panel_quality_report.csv"


def load_wide(path: pathlib.Path) -> pd.DataFrame:
    """Read a combined CSV (13-line header) and sort by date ascending."""
    df = pd.read_csv(path, skiprows=12, dtype=str, keep_default_na=False)
    df.columns = [str(col).strip() for col in df.columns]
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], format="%m/%d/%Y")
    df = df.sort_values(date_col).reset_index(drop=True)
    return df


def to_numeric(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    values = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    return pd.concat([df[[date_col]], values], axis=1)


def daily_returns(numeric_df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Daily pct change on the full date index; missing neighbors stay NaN."""
    values = numeric_df.iloc[:, 1:].pct_change(fill_method=None)
    return pd.concat([numeric_df[[date_col]], values], axis=1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    nav = load_wide(NAV_FILE)
    etf = load_wide(ETF_FILE)
    nav_num = to_numeric(nav, "Date")
    etf_num = to_numeric(etf, "Date")

    fund_ret = daily_returns(nav_num, "Date")
    merged = fund_ret.merge(etf_num, on="Date", how="inner")

    fund_cols = list(fund_ret.columns[1:])
    etf_cols = list(etf_num.columns[1:])
    panel_fund = merged[["Date", *fund_cols]]
    panel_etf = merged[["Date", *etf_cols]]

    panel_fund.to_csv(FUND_PANEL, index=False, na_rep="")
    panel_etf.to_csv(ETF_PANEL, index=False, na_rep="")

    quality_rows = []
    for col in fund_cols:
        mask = panel_fund[col].notna()
        obs = int(mask.sum())
        quality_rows.append(
            {
                "ticker": col,
                "obs": obs,
                "start": panel_fund.loc[mask, "Date"].min().date() if obs else "",
                "end": panel_fund.loc[mask, "Date"].max().date() if obs else "",
            }
        )
    quality = pd.DataFrame(quality_rows).sort_values("ticker").reset_index(drop=True)
    quality.to_csv(QUALITY_REPORT, index=False)

    low_sample = quality[quality["obs"] < 1000]
    print(f"Funds: {len(fund_cols)}, ETFs: {len(etf_cols)}")
    print(f"Common trading days: {len(panel_fund)}")
    print(
        f"Range: {panel_fund['Date'].iloc[0].date()} .. "
        f"{panel_fund['Date'].iloc[-1].date()}"
    )
    print(f"Funds with <1000 observations: {len(low_sample)}")
    if not low_sample.empty:
        print(low_sample.to_string(index=False))
    print(f"Saved: {FUND_PANEL}")
    print(f"Saved: {ETF_PANEL}")
    print(f"Saved: {QUALITY_REPORT}")


if __name__ == "__main__":
    main()
