"""Shared v4 configuration: paths, ETF universe, and thresholds."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]

EVENT_INPUTS = ROOT / "01_数据" / "event_study_inputs"
PROCESSED = ROOT / "01_数据" / "processed_returns"
MIDDLE = ROOT / "04_结果" / "最新成果" / "中间文档"
RESULT_ROOT = ROOT / "04_结果"
V4_OUT = RESULT_ROOT / "v4_中间结果"
BACKUP_EXT_DIR = RESULT_ROOT / "备份" / "扩展ETF_仅备份"

ORIGINAL19 = {
    "SPY", "QQQ", "IWM", "TLT", "TIP", "EEM", "LQD", "HYG", "UUP",
    "SLV", "JNK", "GLD", "GDX", "XLV", "XLU", "XLE", "XLF", "XLK", "FXY",
}

MONEY_FUNDS = {"MPIXX", "MPSXX"}

FUND_PANEL = EVENT_INPUTS / "panel_fund_returns_adj.csv"
ETF19_PANEL = EVENT_INPUTS / "panel_etf_returns_adj.csv"
EXTERNAL_DAILY = EVENT_INPUTS / "external_daily.csv"
V4_ETF19_PANEL = PROCESSED / "v4_etf19_panel.csv"
V4_EXTERNAL_PANEL = PROCESSED / "v4_external_panel.csv"

V3_PASS = MIDDLE / "全部ETF特有" / "v3_dual_criteria_pass.csv"
PAIR_STRICT = MIDDLE / "通用" / "文件" / "pair_strict_pass.csv"

THRESHOLD_GRID_FULL = [50, 80, 100, 120]
THRESHOLD_GRID_FROZEN = [10, 15, 20, 30]
RECOMMENDED_FULL_TRADES = 120
RECOMMENDED_FROZEN_TRADES = 30
