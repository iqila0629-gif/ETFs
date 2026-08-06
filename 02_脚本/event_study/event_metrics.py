"""Shared metrics and decision rules for the ETF -> fund event study."""

from __future__ import annotations

import pandas as pd


def condition_metrics(mask: pd.Series, tomorrow: pd.Series) -> dict[str, float | int]:
    """Conditional next-day statistics for one fund under one event mask.

    Return averages are expressed in percent. Tomorrow returns equal to zero
    count toward N and the conditional expectation but not toward up/down.
    """
    vals = tomorrow[mask].dropna()
    n = int(vals.size)
    if n == 0:
        return {
            "n": 0,
            "up_n": 0,
            "down_n": 0,
            "p_up": float("nan"),
            "p_down": float("nan"),
            "avg_up": float("nan"),
            "avg_down": float("nan"),
            "expected": float("nan"),
        }

    up = vals[vals > 0]
    down = vals[vals < 0]
    up_n = int(up.size)
    down_n = int(down.size)
    return {
        "n": n,
        "up_n": up_n,
        "down_n": down_n,
        "p_up": up_n / n,
        "p_down": down_n / n,
        "avg_up": up.mean() * 100 if up_n else float("nan"),
        "avg_down": down.mean() * 100 if down_n else float("nan"),
        "expected": vals.mean() * 100,
    }


def shortlist(
    df: pd.DataFrame,
    min_n: int = 200,
    min_abs_expected: float = 0.15,
    min_p: float = 0.53,
) -> pd.DataFrame:
    """Research shortlist: enough samples, meaningful expectation, biased odds."""
    valid = df["n"] >= min_n
    meaningful = df["expected"].abs() >= min_abs_expected
    biased = df[["p_up", "p_down"]].max(axis=1) >= min_p
    return df[valid & meaningful & biased].copy()


def add_decision(
    df: pd.DataFrame,
    min_n: int = 200,
    min_p: float = 0.55,
    min_abs_return: float = 0.2,
) -> pd.DataFrame:
    """Strict trade rule: direction probability and average return both pass."""
    out = df.copy()
    decisions = []
    predicted = []
    for _, row in out.iterrows():
        if row["n"] >= min_n and row["p_up"] >= min_p and row["avg_up"] >= min_abs_return:
            decisions.append("predict_up")
            predicted.append(row["avg_up"])
        elif row["n"] >= min_n and row["p_down"] >= min_p and row["avg_down"] <= -min_abs_return:
            decisions.append("predict_down")
            predicted.append(row["avg_down"])
        else:
            decisions.append("no_trade")
            predicted.append("")
    out["decision"] = decisions
    out["predicted_return"] = predicted
    return out


def fund_group(ticker: str) -> str:
    if ticker.endswith("SX"):
        return "inverse"
    if ticker.startswith("U"):
        return "ultra_long"
    return "long"
