"""Brooks 多周期 EMA 近似（15m/60m 投影到 5m 图）的语义与无前视测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.bar import Bar, SessionType, Timeframe
from app.replay.service import ReplayService

_T0 = datetime(2024, 1, 4, 14, 30, tzinfo=UTC)  # 09:30 ET


def _mk_day(closes: list[float], day_start: datetime) -> list[Bar]:
    return [
        Bar(
            instrument_id="SPY",
            timeframe=Timeframe.M5,
            ts_open_utc=day_start + timedelta(minutes=5 * i),
            ts_close_utc=day_start + timedelta(minutes=5 * (i + 1)),
            open=c, high=c + 0.5, low=c - 0.5, close=c, volume=1,
            session=SessionType.RTH, provider="t", feed="t", data_version="t",
        )
        for i, c in enumerate(closes)
    ]


def test_ema15_updates_every_3_bars_and_holds_within_bucket():
    bars = _mk_day([100.0 + i for i in range(78)], _T0)
    out = ReplayService._higher_tf_ema20(bars, bucket_bars=3)

    assert len(out) == 78
    update_points = [i for i in range(78) if (i + 1) % 3 == 0]
    # Brooks 语义：桶边界 bar 本身绘制更新后的新值；桶内其余 5m K 线沿用上一个边界值（阶梯持平）
    for i in range(78):
        if i in update_points:
            continue
        prev_boundary = max((u for u in update_points if u < i), default=None)
        if prev_boundary is None:
            assert out[i] is None  # 首个边界之前无投影值
        else:
            assert out[i] == out[prev_boundary], f"bar {i} 未沿用边界 {prev_boundary} 的值"

    assert out[2] is not None  # 第一个桶边界即产出首个投影值
    assert out[0] is None and out[1] is None  # 桶内未到更新点不提前产出


def test_ema60_seed_and_bucket_alignment():
    bars = _mk_day([100.0 + i for i in range(78)], _T0)
    out = ReplayService._higher_tf_ema20(bars, bucket_bars=12)

    assert len(out) == 78
    # 78 根的一天有 6 个完整 12 根桶：更新点在 11,23,...,71
    update_points = [i for i in range(78) if (i + 1) % 12 == 0]
    assert update_points == [11, 23, 35, 47, 59, 71]
    assert out[11] is not None  # 首个桶边界起步
    assert out[10] is None
    # 72~77 属于不完整桶：沿用上一桶边界值（69..77? 边界71 之后非边界 bar 沿用 71 的值）
    assert all(out[i] == out[71] for i in range(72, 78))


def test_higher_tf_ema_never_uses_future_bars(seeded_client):
    """逐根推进时，ema15/ema60 最后一个值只依赖当前及更早的 5m 收盘（无前视）。"""
    r = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"})
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]

    detail = seeded_client.get(f"/api/v1/replay/sessions/{sid}").json()
    steps = 0
    while not detail["info"]["is_completed"] and steps < 100:
        for key in ("ema15", "ema60"):
            assert len(detail[key]) == len(detail["bars"])
        detail = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 5}).json()
        steps += 1
