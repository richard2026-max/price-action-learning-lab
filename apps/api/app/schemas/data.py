"""数据管理相关 Pydantic schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SeedIn(BaseModel):
    start: str = Field(..., description="YYYY-MM-DD")
    end: str = Field(..., description="YYYY-MM-DD")
    seed: int | None = None  # 缺省用设置中的 synthetic_seed（可复现）


class SeedOut(BaseModel):
    days: int
    bars_1m: int
    bars_5m: int
    duplicate_count_1m: int
    duplicate_count_5m: int
    manifest_1m: dict
    manifest_5m: dict
