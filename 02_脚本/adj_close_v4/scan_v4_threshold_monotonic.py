"""v4 threshold monotonicity: -1%/-2%/-3% buckets and per-strategy threshold sweep."""

from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

import config
import scan_v4_thresholds as s4
import select_v4_strategies as sel
from analyze_v4_oos import metric_dict

OUT_DIR = config.V4_OUT / "v4_稳健性分析"
TEST_START = np.datetime64("2025-01-01")
THRESHOLDS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
BUCKET_EDGES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, np.inf]


def load_master() -> tuple[pd.DataFrame, list[str], set[str]]:
    master = s4.load_master()
    fund_cols = list(pd.read_csv(config.FUND_PANEL).columns[1:])
    external_cols = set(pd.read_csv(config.V4_EXTERNAL_PANEL).columns) - {"Date"}
    non_fund = {"Date"} | external_cols
    all_etfs = {c for c in master.columns if c not in set(fund_cols) and c not in non_fund}
    return master, fund_cols, all_etfs


def part_direction(token: str) -> tuple[str, bool]:
    if token.startswith("self_"):
        base = token[len("self_"):]
        if base.endswith("down") or base == "lt-2":
            return "self", False
        return "self", True
    if token.startswith("ext_"):
        import scan_v4_conditions as sc
        for safe, _col in sc.EXTERNAL_COLS.items():
            prefix = f"ext_{safe}_"
            if token.startswith(prefix):
                op = token[len(prefix):]
                if op.startswith("ge"):
                    return "ext", True
                if op.startswith("le"):
                    return "ext", False
                return "ext", op == "up"
        return "ext", True
    base = token.split("_", 1)[1] if "_" in token else token
    if base.endswith("down") or base.endswith("lt-2"):
        return "etf", False
    return "etf", True


def delivered_magnitude(token: str) -> float:
    if token.startswith("self_"):
        suffix = token[len("self_"):]
        if suffix in ("big_up", "big_down"):
            return 2.0
        return 0.0
    if token.startswith("ext_"):
        import scan_v4_conditions as sc
        for safe, _col in sc.EXTERNAL_COLS.items():
            prefix = f"ext_{safe}_"
            if token.startswith(prefix):
                op = token[len(prefix):]
                if op in ("up", "down"):
                    return 0.0
                return abs(float(op[2:].replace("_", ".")))
        return 0.0
    suffix = token.split("_", 1)[1] if "_" in token else ""
    if suffix in ("big_up", "big_down"):
        return 1.0
    if suffix in ("gt2", "lt-2"):
        return 2.0
    return 0.0


def scan_magnitudes(token: str) -> list[float]:
    if re.match(r"self_\d", token):
        return [1.0, 2.0, 3.0, 4.0, 5.0]
    base = delivered_magnitude(token)
    vals = sorted({round(base + k * 0.5, 2) for k in range(-4, 5)})
    return [v for v in vals if v >= 0.0]


def build_scan_part(master, part, ticker, all_etfs, scan_token, th_pct):
    if part == scan_token and re.match(r"self_\d", scan_token):
        n = int(th_pct)
        r = master[ticker]
        m = (r < 0) if scan_token.endswith("down") else (r > 0)
        for k in range(1, n):
            m = m & (r.shift(k) < 0 if scan_token.endswith("down") else r.shift(k) > 0)
        return m
    if part == scan_token:
        kind, positive = part_direction(scan_token)
        if kind == "self":
            r = master[ticker].to_numpy(dtype=float) * 100.0
        elif kind == "ext":
            import scan_v4_conditions as sc
            col = None
            for safe, c in sc.EXTERNAL_COLS.items():
                if part.startswith(f"ext_{safe}_"):
                    col = c
                    break
            if col is None:
                raise ValueError(part)
            r = master[col].to_numpy(dtype=float)
        else:
            etf = part.split("_", 1)[0]
            r = master[etf].to_numpy(dtype=float)
        if positive:
            return pd.Series(r >= th_pct, index=master.index)
        return pd.Series(r <= -th_pct, index=master.index)
    return sel.build_unified_mask(master, part, ticker, all_etfs)


def is_scan_token(part: str, all_etfs: set[str]) -> bool:
    if part.startswith("self_"):
        return True
    if part.startswith("ext_"):
        return True
    first = part.split("_", 1)[0]
    if first not in all_etfs:
        return False
    suffix = part[len(first) + 1:] if "_" in part else ""
    return suffix in {"up", "down", "big_up", "big_down", "gt2", "lt-2"}


def strategy_parts(condition: str, all_etfs: set[str]) -> list[str]:
    if condition.startswith("combo_"):
        return condition[len("combo_"):].split("__")
    tokens = condition.split("_")
    if (
        len(tokens) in (4, 6)
        and tokens[0] in all_etfs
        and tokens[2] in all_etfs
        and set(tokens[1::2]) <= {"up", "down"}
    ):
        return [f"{tokens[i]}_{tokens[i + 1]}" for i in range(0, len(tokens), 2)]
    return [condition]


def scan_tokens(condition: str, all_etfs: set[str]) -> list[str]:
    out = []
    for p in strategy_parts(condition, all_etfs):
        if is_scan_token(p, all_etfs):
            out.append(p)
    return out


def bucket_stats(vals: np.ndarray, targets: np.ndarray) -> dict:
    n = int(vals.size)
    if n == 0:
        return {"n": 0, "avg": float("nan"), "hit": float("nan"), "std": float("nan")}
    std = float(vals.std(ddof=1)) if n > 1 else float("nan")
    return {
        "n": n,
        "avg": float(vals.mean()),
        "hit": float((vals > 0).mean()),
        "std": std,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    master, fund_cols, all_etfs = load_master()
    dates = master["Date"].to_numpy()

    print("D1 self-return buckets...", flush=True)
    bucket_rows = []
    neg_edges = [-np.inf, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0]
    for ticker in fund_cols:
        r = master[ticker].to_numpy(dtype=float) * 100.0
        target = np.full(r.size, np.nan)
        target[:-1] = r[1:]
        for i in range(len(neg_edges) - 1):
            lo = neg_edges[i]
            hi = neg_edges[i + 1]
            if np.isneginf(lo):
                keep = r <= hi
            else:
                keep = (r > lo) & (r <= hi)
            valid = keep & np.isfinite(target)
            stats = bucket_stats(target[valid], target)
            bucket_rows.append({
                "ticker": ticker,
                "bucket_lo": lo if not np.isneginf(lo) else "-inf",
                "bucket_hi": hi,
                **stats,
            })
    pd.DataFrame(bucket_rows).to_csv(OUT_DIR / "v4_self_return_buckets.csv", index=False)

    print("D1.5 fund streak event study...", flush=True)
    streak_rows = []
    for ticker in fund_cols:
        r = master[ticker].to_numpy(dtype=float) * 100.0
        target = np.full(r.size, np.nan)
        target[:-1] = r[1:]
        for n in range(1, 6):
            down_mask = r < 0
            up_mask = r > 0
            for k in range(1, n):
                down_mask = down_mask & (np.roll(r, k) < 0)
                up_mask = up_mask & (np.roll(r, k) > 0)
            down_mask[:n - 1] = False
            up_mask[:n - 1] = False
            for direction, mask in [("down", down_mask), ("up", up_mask)]:
                valid = mask & np.isfinite(target)
                stats = bucket_stats(target[valid], target)
                streak_rows.append({
                    "ticker": ticker,
                    "direction": direction,
                    "streak_days": n,
                    **stats,
                })
    pd.DataFrame(streak_rows).to_csv(OUT_DIR / "v4_streak_event_study.csv", index=False)
    print("D2 strategy threshold sweep...", flush=True)
    mapping = pd.read_csv(config.V4_OUT / "v4_strategy_mapping_m30_v2.csv", keep_default_na=False)
    target_cache: dict[tuple[str, int, bool], np.ndarray] = {}
    rows = []
    for r in mapping.itertuples(index=False):
        ticker = str(r.ticker)
        condition = str(r.condition)
        horizon = int(r.horizon)
        source = str(r.source)
        for token in scan_tokens(condition, all_etfs):
            parts = strategy_parts(condition, all_etfs)
            is_streak = bool(re.match(r"self_\d", token))
            scan_values = scan_magnitudes(token)
            for th in scan_values:
                mask = None
                for p in parts:
                    pm = build_scan_part(master, p, ticker, all_etfs, token, th)
                    mask = pm if mask is None else (mask & pm)
                strict = source in ("pair_scan", "triple_scan", "condition_expansion")
                key = (ticker, horizon, strict)
                if key not in target_cache:
                    target_cache[key] = s4.multi_day_target(master, ticker, horizon, strict)
                target = target_cache[key]
                ev, vals, trade = s4.evaluate(mask, target, dates, *s4.params_for(source))
                td = ev[trade]
                tv = vals[trade]
                full = metric_dict(tv)
                te_keep = td >= TEST_START
                test = metric_dict(tv[te_keep])
                rows.append({
                    "ticker": ticker,
                    "strategy_no": int(r.strategy_no),
                    "condition": condition,
                    "scan_token": token,
                    "horizon": horizon,
                    "scan_kind": "streak_days" if is_streak else "threshold",
                    "delivered_threshold": delivered_magnitude(token),
                    "threshold": th,
                    "full_avg": full["avg"],
                    "full_trades": full["trades"],
                    "full_hit": full["hit"],
                    "full_std": full["std"],
                    "test_avg": test["avg"],
                    "test_trades": test["trades"],
                    "test_hit": test["hit"],
                    "test_std": test["std"],
                })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "v4_threshold_monotonic.csv", index=False)
    print("threshold sweep rows:", len(df))

    if len(df):
        df = df.copy()
        df["direction"] = df["scan_token"].apply(lambda t: "down" if (t.endswith("down") or t.endswith("lt-2")) else "up")
        mono = []
        for (ticker, condition, token, horizon, direction), g in df.groupby(["ticker", "condition", "scan_token", "horizon", "direction"]):
            g = g.sort_values("threshold")
            avg = g["full_avg"].to_numpy(dtype=float)
            ok = np.isfinite(avg)
            if ok.sum() < 2:
                continue
            if direction == "down":
                rho = float(np.corrcoef(g["threshold"][ok], avg[ok])[0, 1]) if ok.sum() > 1 else float("nan")
                monotone = bool(avg[ok][-1] >= avg[ok].max() and np.all(np.diff(avg[ok]) >= 0))
            else:
                rho = float(np.corrcoef(g["threshold"][ok], avg[ok])[0, 1]) if ok.sum() > 1 else float("nan")
                monotone = bool(avg[ok][0] >= avg[ok].max() and np.all(np.diff(avg[ok]) <= 0))
            mono.append({
                "ticker": ticker,
                "condition": condition,
                "scan_token": token,
                "horizon": horizon,
                "direction": direction,
                "spearman_like_rho": rho if np.isfinite(rho) else "",
                "monotone": monotone,
            })
        pd.DataFrame(mono).to_csv(OUT_DIR / "v4_threshold_monotonic_summary.csv", index=False)
        print("monotonic summary rows:", len(mono))

    print("done")


if __name__ == "__main__":
    main()








