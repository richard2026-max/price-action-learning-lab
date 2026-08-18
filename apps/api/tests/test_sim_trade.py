"""模拟交易执行引擎与 MFE/MAE 测试（Phase 2）。"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.bar import Bar, SessionType, Timeframe
from app.models.orm import SimTradeORM
from app.services.sim_trade_service import SimTradeService


def test_sim_trade_market_order_and_advancement(seeded_client):
    # 1. 创建回放会话
    s = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"}).json()
    sid = s["session_id"]
    current_price = s["bars"][-1]["close"]

    # 2. 下达市价多单（Market Long）
    stop = current_price - 2.0
    target = current_price + 4.0
    r = seeded_client.post(
        f"/api/v1/trades/sessions/{sid}",
        json={
            "side": "long",
            "order_type": "market",
            "planned_entry_price": current_price,
            "stop_price": stop,
            "target_price": target,
            "reasons": ["突破EMA20", "顺大趋势"],
        },
    )
    assert r.status_code == 201, r.text
    trade = r.json()
    assert trade["status"] == "open"
    assert trade["actual_entry_price"] == current_price
    assert trade["initial_risk"] == 2.0

    # 3. 推进回放 5 根，检查 MFE/MAE 实时追踪更新
    seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 5})

    trades_list = seeded_client.get(f"/api/v1/trades/sessions/{sid}").json()
    assert len(trades_list) == 1
    t = trades_list[0]
    assert t["mfe_price"] is not None
    assert t["mae_price"] is not None
    assert t["mfe_in_r"] is not None


def test_sim_trade_limit_order_matching(seeded_client):
    # 1. 创建回放会话
    s = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"}).json()
    sid = s["session_id"]
    current_price = s["bars"][-1]["close"]

    # 2. 下达限价多单（挂在当前价下方 1.0 处）
    limit_price = round(current_price - 1.0, 2)
    stop = limit_price - 2.0
    target = limit_price + 3.0
    r = seeded_client.post(
        f"/api/v1/trades/sessions/{sid}",
        json={
            "side": "long",
            "order_type": "limit",
            "planned_entry_price": limit_price,
            "stop_price": stop,
            "target_price": target,
            "reasons": ["限价回踩挂单", "支撑位买入"],
        },
    )
    assert r.status_code == 201
    trade = r.json()
    assert trade["status"] == "pending"
    assert trade["actual_entry_price"] is None


def test_sim_trade_pessimistic_exit_rule():
    """单元测试：验证 ADR-005 保守结算（同根 Bar 同时触及 Target 与 Stop 时，判为止损先触发）。"""
    bar = Bar(
        instrument_id="SPY", timeframe=Timeframe.M5,
        ts_open_utc=datetime.now(UTC), ts_close_utc=datetime.now(UTC),
        open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0,
        session=SessionType.RTH, provider="synthetic", feed="t", data_version="t",
    )

    t = SimTradeORM(
        id="test-1", session_id="s1", instrument_id="SPY", provider="synthetic",
        day=datetime.now(UTC).date(), side="long", order_type="market", status="open",
        order_bar_index=0, order_time_utc=datetime.now(UTC),
        planned_entry_price=100.0, actual_entry_price=100.0,
        stop_price=96.0, target_price=104.0, initial_risk=4.0,
    )

    exited, exit_price, reason = SimTradeService._check_exit(t, bar)
    assert exited is True
    # 保守判定：止损触发
    assert reason == "stop"
    assert exit_price == 96.0
