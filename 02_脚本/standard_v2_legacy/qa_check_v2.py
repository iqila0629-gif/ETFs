"""QA checks for standard_v2 deliverables."""

from __future__ import annotations

import pathlib
import sys

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
DST = ROOT / "analysis_results" / "standard_v2"


def read13(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=12, dtype=str, keep_default_na=False)
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    col = df.columns[1]
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    issues: list[str] = []

    passdf = pd.read_csv(DST / "v2_dual_criteria_pass.csv", keep_default_na=False)
    for c in ["full_avg", "full_hit", "frozen_avg", "frozen_hit"]:
        passdf[c] = pd.to_numeric(passdf[c], errors="coerce")
    dup = passdf.duplicated(subset=["ticker", "condition", "horizon"]).sum()
    if dup:
        issues.append(f"pass: {dup} duplicate ticker/condition/horizon rows")
    bad = passdf[
        ~(
            (passdf["full_avg"].abs() >= 0.2)
            & (passdf["full_trades"] >= 50)
            & (passdf["full_hit"] > 0.55)
            & (passdf["frozen_avg"].abs() >= 0.2)
            & (passdf["frozen_trades"] >= 10)
            & (passdf["frozen_hit"] >= 0.55)
        )
    ]
    if len(bad):
        issues.append(f"pass: {len(bad)} rows fail required criteria: {bad[['ticker','condition','horizon']].head(5).to_dict('records')}")

    summary = pd.read_csv(DST / "v2_dual_criteria_summary.csv", keep_default_na=False)
    if summary["ticker"].duplicated().sum():
        issues.append("summary: duplicate ticker rows")
    pass_keys = set(zip(passdf["ticker"], passdf["condition"], passdf["horizon"]))
    for _, r in summary.iterrows():
        if (r["ticker"], r["condition"], int(r["horizon"])) not in pass_keys:
            issues.append(f"summary: {r['ticker']} best not in pass")

    mapping = pd.read_csv(DST / "v2_strategy_mapping.csv", keep_default_na=False)
    if len(mapping) != len(summary):
        issues.append(f"mapping rows {len(mapping)} != summary rows {len(summary)}")

    # company best tables
    for name, hit_req in [
        ("v2_company_daily_best_full_history.csv", 0.55),
        ("v2_company_daily_best_frozen.csv", 0.55),
    ]:
        path = DST / name
        header = pd.read_csv(path, nrows=12, header=None, skiprows=1)
        hit_row = header.iloc[1].astype(str).str.replace("", "", regex=False)
        df = read13(path)
        if df["Date"].isna().any():
            issues.append(f"{name}: unparseable dates")
        if df["Date"].duplicated().sum():
            issues.append(f"{name}: duplicate dates")
        if not (df["Date"].diff().dropna() < pd.Timedelta(0)).all():
            issues.append(f"{name}: dates not descending")
        for col in df.columns[1:]:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if vals.empty:
                continue
            if abs(vals.mean()) < 0.2:
                issues.append(f"{name}: {col} avg {vals.mean():.4f} < 0.2")
            hit = (vals > 0).sum() / len(vals)
            if hit <= hit_req:
                issues.append(f"{name}: {col} hit {hit:.4f} <= {hit_req}")

    # final output files vs pass stats
    full_files = {p.stem: p for p in (DST / "final_outputs_dual_full_history").glob("*.csv")}
    frozen_files = {p.stem: p for p in (DST / "final_outputs_dual_frozen").glob("*.csv")}
    expected_names = set()
    for _, r in passdf.iterrows():
        name = f"{r['ticker']}__{r['condition']}" + (f"__N{int(r['horizon'])}" if int(r["horizon"]) > 1 else "")
        expected_names.add(name)
    missing_full = expected_names - set(full_files)
    missing_frozen = expected_names - set(frozen_files)
    extra_full = set(full_files) - expected_names
    extra_frozen = set(frozen_files) - expected_names
    if missing_full:
        issues.append(f"missing full files: {len(missing_full)} {sorted(missing_full)[:5]}")
    if missing_frozen:
        issues.append(f"missing frozen files: {len(missing_frozen)} {sorted(missing_frozen)[:5]}")
    if extra_full:
        issues.append(f"extra full files: {len(extra_full)} {sorted(extra_full)[:5]}")
    if extra_frozen:
        issues.append(f"extra frozen files: {len(extra_frozen)} {sorted(extra_frozen)[:5]}")

    stats_map = {
        (r["ticker"], r["condition"], int(r["horizon"])): r
        for _, r in passdf.iterrows()
    }
    checked = 0
    for name, p in full_files.items():
        parts = name.split("__", 1)
        if len(parts) != 2:
            continue
        ticker = parts[0]
        rest = parts[1]
        horizon = 1
        if "__N" in rest:
            rest, h = rest.split("__N")
            horizon = int(h)
        key = (ticker, rest, horizon)
        row = stats_map.get(key)
        if row is None:
            issues.append(f"full file {name}: no matching pass row")
            continue
        df = read13(p)
        vals = df[df.columns[1]].dropna()
        if abs(float(vals.mean()) - row["full_avg"]) > 1e-4:
            issues.append(f"full file {name}: avg {vals.mean():.4f} != pass {row['full_avg']:.4f}")
        hit = (vals > 0).sum() / len(vals)
        if abs(hit - row["full_hit"]) > 1e-4:
            issues.append(f"full file {name}: hit {hit:.4f} != pass {row['full_hit']:.4f}")
        if len(vals) != row["full_trades"]:
            issues.append(f"full file {name}: trades {len(vals)} != pass {row['full_trades']}")
        checked += 1
    for name, p in frozen_files.items():
        parts = name.split("__", 1)
        if len(parts) != 2:
            continue
        ticker = parts[0]
        rest = parts[1]
        horizon = 1
        if "__N" in rest:
            rest, h = rest.split("__N")
            horizon = int(h)
        row = stats_map.get((ticker, rest, horizon))
        if row is None:
            issues.append(f"frozen file {name}: no matching pass row")
            continue
        df = read13(p)
        vals = df[df.columns[1]].dropna()
        if len(vals) != row["frozen_trades"]:
            issues.append(f"frozen file {name}: trades {len(vals)} != pass {row['frozen_trades']}")
        if len(vals):
            if abs(float(vals.mean()) - row["frozen_avg"]) > 1e-4:
                issues.append(f"frozen file {name}: avg {vals.mean():.4f} != pass {row['frozen_avg']:.4f}")
            hit = (vals > 0).sum() / len(vals)
            if abs(hit - row["frozen_hit"]) > 1e-4:
                issues.append(f"frozen file {name}: hit {hit:.4f} != pass {row['frozen_hit']:.4f}")

    # weird values
    for folder_name in ["final_outputs_dual_full_history", "final_outputs_dual_frozen"]:
        for p in (DST / folder_name).glob("*.csv"):
            df = read13(p)
            vals = df[df.columns[1]].dropna()
            if (vals.abs() > 100).any():
                issues.append(f"{p.name}: {int((vals.abs() > 100).sum())} values >100%")
            if len(vals) == 0:
                issues.append(f"{p.name}: empty data")

    print(f"issues: {len(issues)}")
    for msg in issues[:60]:
        print(" -", msg)
    if not issues:
        print("ALL CHECKS PASSED")
    print(f"files checked: {checked}")


if __name__ == "__main__":
    main()
