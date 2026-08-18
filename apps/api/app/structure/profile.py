"""版本化 detector 参数 profile（MVP-B）。

参数与 docs/concepts/*.md 中的 mechanical_definition 一一对应；
变更参数必须升版本并在 spec 的变更记录注明。
"""

from __future__ import annotations

DETECTOR_PROFILE_VERSION = "mvp-c-0.1.0"

PARAMS: dict[str, float | int] = {
    "doji_body_ratio_max": 0.25,             # doji：实体/波幅 ≤ 0.25（保守宽近似，原书更紧）
    "trend_bar_strong_body_ratio": 0.6,      # 强趋势K线：实体占比 ≥ 0.6
    "trend_bar_strong_relative_range": 1.2,  # 且波幅 ≥ 近20根均值的 1.2 倍
    "relative_range_window": 20,             # relative_range 回看窗口（不含当前根）
    # ---- MVP-C 结构层 ----
    "swing_lookback": 3,                     # swing pivot 强度（左右各 N 根）
    "context_drift_window": 20,              # 净漂移上下文窗口
}


def params() -> dict[str, float | int]:
    return dict(PARAMS)


def profile_version() -> str:
    return DETECTOR_PROFILE_VERSION
