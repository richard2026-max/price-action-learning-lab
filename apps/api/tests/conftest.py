"""测试夹具：临时数据目录 + 应用 + 客户端 + 预置数据。不依赖网络（合成数据）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

SEED_START = date(2024, 1, 2)
SEED_END = date(2024, 1, 12)  # 9 个交易日，含 2024-01-03（无早收）；2024-01-15 MLK 假日在范围外


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(data_dir=tmp_path / "data", sqlite_path=tmp_path / "app.sqlite")
    application = create_app(settings)
    return application


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def seeded_client(app) -> TestClient:
    """预置 2024-01-02 ~ 2024-01-12 合成数据的客户端。"""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/data/seed",
        json={"start": SEED_START.isoformat(), "end": SEED_END.isoformat()},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture(scope="session")
def raw_bars():
    """直接生成 1m/5m 数据（供纯服务层测试，不经 HTTP）。"""
    from app.domain.instrument import SPY_SYNTH
    from app.services.aggregation import aggregate_day_1m_to_5m
    from app.services.calendar import XNYSCalendar
    from app.services.synthetic import generate_range_1m

    cal = XNYSCalendar()
    bars_1m = generate_range_1m(SPY_SYNTH, SEED_START, SEED_END, cal, global_seed=42)
    bars_5m: list = []
    for day in cal.trading_days(SEED_START, SEED_END):
        day_1m = [b for b in bars_1m if b.ts_open_utc.date() == day]
        bars_5m.extend(aggregate_day_1m_to_5m(day_1m, day, cal))
    return bars_1m, bars_5m, cal
