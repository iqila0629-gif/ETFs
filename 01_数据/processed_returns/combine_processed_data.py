"""Combine processed NAV / ETF CSV files into one wide table per group."""

from __future__ import annotations

import csv
import pathlib
import sys

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parent
NAV_DIR = ROOT / "processed_nav"
ETF_DIR = ROOT / "processed_etf_returns"
NAV_OUT = ROOT / "combined_profunds_nav.csv"
ETF_OUT = ROOT / "combined_etf_returns.csv"

# Source files reserve 12 lines before the "Date,Value" header on line 13.
HEADER_LINES = 12
STAT_NAMES = [
    "Hit Ratio",
    "Up Count",
    "Down Count",
    "Average",
    "Max",
    "Min",
    "Count",
    "Std",
    "Sum",
]


def read_source_stats(path: pathlib.Path) -> dict[str, float]:
    stats: dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for line in fh:
            parts = line.rstrip("\r\n").split(",")
            if len(parts) == 2 and parts[0] in STAT_NAMES:
                stats[parts[0]] = float(parts[1])
    return stats


def load_series(folder: pathlib.Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    files = sorted(folder.glob("*.csv"))
    for file in files:
        ticker = file.stem
        df = pd.read_csv(file, skiprows=HEADER_LINES, dtype=str, keep_default_na=False)
        if list(df.columns) != ["Date", ticker] and len(df.columns) != 2:
            warnings.append(f"{file.name}: unexpected columns {list(df.columns)}")
        df.columns = ["Date", ticker]
        df["Date"] = df["Date"].str.strip()
        df[ticker] = df[ticker].str.strip()

        dup = df["Date"].duplicated().sum()
        if dup:
            warnings.append(f"{file.name}: dropped {dup} duplicate date(s)")
            df = df.drop_duplicates(subset=["Date"], keep="first")

        parsed = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
        bad = parsed.isna().sum()
        if bad:
            warnings.append(f"{file.name}: {bad} unparseable date(s)")
            df = df[parsed.notna()].copy()

        frames.append(df[["Date", ticker]])

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="Date", how="outer")

    merged["_sort"] = pd.to_datetime(merged["Date"], format="%m/%d/%Y")
    merged = merged.sort_values("_sort", ascending=False).drop(columns="_sort")
    merged = merged.reset_index(drop=True)
    return merged, [f.stem for f in files], warnings


def fmt_number(value: float, is_count: bool = False) -> str:
    if value != value:  # NaN
        return ""
    if is_count:
        return str(int(value))
    return f"{value:.6f}"


def compute_one_stat(name: str, col: pd.Series) -> str:
    if name == "Hit Ratio":
        up = (col > 0).sum()
        down = (col < 0).sum()
        value = up / (up + down) if (up + down) else float("nan")
        return fmt_number(value)
    if name == "Up Count":
        return fmt_number(float((col > 0).sum()), is_count=True)
    if name == "Down Count":
        return fmt_number(float((col < 0).sum()), is_count=True)
    if name == "Average":
        return fmt_number(col.mean())
    if name == "Max":
        return fmt_number(col.max())
    if name == "Min":
        return fmt_number(col.min())
    if name == "Count":
        return fmt_number(float(col.count()), is_count=True)
    if name == "Std":
        return fmt_number(col.std(ddof=1))
    if name == "Sum":
        return fmt_number(col.sum())
    raise ValueError(f"unknown stat: {name}")


def read_source_stats_map(folder: pathlib.Path) -> dict[str, dict[str, float]]:
    return {file.stem: read_source_stats(file) for file in sorted(folder.glob("*.csv"))}


def verify_stats(df: pd.DataFrame, folder: pathlib.Path) -> list[str]:
    mismatches: list[str] = []
    for file in sorted(folder.glob("*.csv")):
        ticker = file.stem
        source = read_source_stats(file)
        if not source:
            mismatches.append(f"{file.name}: source stats block not found")
            continue
        col = pd.to_numeric(df[ticker], errors="coerce")
        computed = {
            "Up Count": float((col > 0).sum()),
            "Down Count": float((col < 0).sum()),
            "Average": col.mean(),
            "Max": col.max(),
            "Min": col.min(),
            "Count": float(col.count()),
            "Std": col.std(ddof=1),
            "Sum": col.sum(),
        }
        up = computed["Up Count"]
        down = computed["Down Count"]
        computed["Hit Ratio"] = up / (up + down) if (up + down) else float("nan")
        for name, value in computed.items():
            source_value = source.get(name)
            if source_value is None:
                continue
            if value != value:  # computed NaN
                if source_value != source_value:
                    continue
                mismatches.append(f"{file.name}: {name} computed NaN, source {source_value}")
                continue
            tolerance = max(1e-2, abs(source_value) * 2e-3)
            if abs(value - source_value) > tolerance:
                mismatches.append(
                    f"{file.name}: {name} computed {value:.6f}, source {source_value:.6f}"
                )
    return mismatches


def write_combined(
    path: pathlib.Path,
    df: pd.DataFrame,
    tickers: list[str],
    source_stats: dict[str, dict[str, float]],
) -> None:
    stats_rows: list[list[str]] = []
    for name in STAT_NAMES:
        row = [name]
        for ticker in tickers:
            source_value = source_stats.get(ticker, {}).get(name)
            if source_value is not None:
                is_count = name in ("Up Count", "Down Count", "Count")
                row.append(fmt_number(source_value, is_count=is_count))
            else:
                col = pd.to_numeric(df[ticker], errors="coerce")
                row.append(compute_one_stat(name, col))
        stats_rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([])
        for row in stats_rows:
            writer.writerow(row)
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Date", *tickers])
        for _, row in df.iterrows():
            values = [row["Date"]]
            for ticker in tickers:
                value = row[ticker]
                values.append("" if pd.isna(value) else value)
            writer.writerow(values)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nav_df, nav_tickers, nav_warnings = load_series(NAV_DIR)
    etf_df, etf_tickers, etf_warnings = load_series(ETF_DIR)

    write_combined(NAV_OUT, nav_df, nav_tickers, read_source_stats_map(NAV_DIR))
    write_combined(ETF_OUT, etf_df, etf_tickers, read_source_stats_map(ETF_DIR))

    nav_mismatches = verify_stats(nav_df, NAV_DIR)
    etf_mismatches = verify_stats(etf_df, ETF_DIR)

    print(f"ProFunds NAV: {len(nav_tickers)} tickers, {len(nav_df)} dates")
    print(f"  range: {nav_df['Date'].iloc[-1]} .. {nav_df['Date'].iloc[0]}")
    print(f"ETF returns: {len(etf_tickers)} tickers, {len(etf_df)} dates")
    print(f"  range: {etf_df['Date'].iloc[-1]} .. {etf_df['Date'].iloc[0]}")
    print(f"Output: {NAV_OUT}")
    print(f"Output: {ETF_OUT}")

    for label, warnings in [("NAV", nav_warnings), ("ETF", etf_warnings)]:
        for warning in warnings:
            print(f"WARN [{label}] {warning}")
    for label, mismatches in [("NAV", nav_mismatches), ("ETF", etf_mismatches)]:
        for mismatch in mismatches:
            print(f"STAT-MISMATCH [{label}] {mismatch}")


if __name__ == "__main__":
    main()
