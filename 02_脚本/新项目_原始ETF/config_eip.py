# -*- coding: utf-8 -*-
"""EIP new-project configuration: paths, clean targets, original-19 ETF universe, thresholds.

Units (follow v4): fund returns are decimals (0.01 = 1%), ETF returns are percents.
"""
from __future__ import annotations

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "01_数据"
PROCESSED_DIR = DATA / "新项目_processed"
PRICE_DIR = DATA / "新项目_基金价格"
CLEANED_DIR = PROCESSED_DIR / "eip_cleaned"

CONFIRMED = DATA / "eip_confirmed.csv"
CLEAN_TARGETS = DATA / "eip_clean_targets.csv"
DATA_INSUFFICIENT = DATA / "eip_data_insufficient.csv"

PANEL_PATH = PROCESSED_DIR / "eip_panel_19etf.csv"
CLEANING_LOG = PROCESSED_DIR / "eip_cleaning_log.csv"

# v4 original 19 ETF (XLC intentionally excluded)
ORIGINAL19 = [
    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP",
    "SLV", "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
]
ORIGINAL19_SET = set(ORIGINAL19)

ETF_PANEL = DATA / "event_study_inputs" / "panel_etf_returns_adj.csv"  # Date + 19 ETF cols (percent)

# results
RESULT_ROOT = ROOT / "04_结果" / "新项目_原始ETF"
MIDDLE = RESULT_ROOT / "中间结果"

# thresholds / windows
CUTOFF = "2025-01-01"
RECOMMENDED_FULL_TRADES = 120
RECOMMENDED_FROZEN_TRADES = 30
MIN_ABS_AVG = 0.2
MIN_FULL_HIT = 0.55
MIN_FROZEN_HIT = 0.55
HORIZONS = [1, 2, 3]
THRESHOLD_GRID_FULL = [50, 80, 100, 120]
THRESHOLD_GRID_FROZEN = [10, 15, 20, 30]

# walk-forward decision (v4 reuse)
DECISION_N = 100
DECISION_P = 0.52
DECISION_ABS = 0.15
RAW_EVENT_MIN = RECOMMENDED_FULL_TRADES + DECISION_N  # 220

# outlier guards (daily returns): fund decimal, ETF percent
FUND_RETURN_CLIP = 0.5
ETF_RETURN_CLIP = 50.0

# download
PERIOD1 = 883612800  # 1998-01-01 UTC


def load_clean_targets() -> pd.DataFrame:
    return pd.read_csv(CLEAN_TARGETS, encoding="utf-8-sig")