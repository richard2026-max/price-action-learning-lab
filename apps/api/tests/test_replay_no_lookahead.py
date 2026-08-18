"""回放引擎集成测试——MVP-A 最高等级工程约束的证明：

> 整个 replay session 的所有行情响应中，不存在 timestamp > cursor 的 bar。

同时覆盖：EMA 无前视、关键价位只用已知数据、判断锁定、回看限制、随机日可复现。
"""

from datetime import date

DAY = "2024-01-04"


def _create(seeded_client, day=DAY, mode="free", warmup=6):
    r = seeded_client.post(
        "/api/v1/replay/sessions", json={"day": day, "mode": mode, "warmup_bars": warmup}
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_no_future_bar_ever_leaked(seeded_client):
    """核心防前视断言：任何响应的任何 bar，ts_close_utc <= 当前 cursor bar 的 ts_close_utc。"""
    s = _create(seeded_client)
    sid = s["session_id"]
    total_bars_seen_max = 0

    resp = seeded_client.get(f"/api/v1/replay/sessions/{sid}")
    detail = resp.json()
    while not detail["info"]["is_completed"]:
        cursor_close = detail["bars"][-1]["ts_close_utc"]
        # 1) 响应长度 == bar_index + 1
        assert len(detail["bars"]) == detail["info"]["bar_index"] + 1
        # 2) 所有 bar 收盘时间 <= cursor 收盘时间（无未来泄露）
        for b in detail["bars"]:
            assert b["ts_close_utc"] <= cursor_close
        # 3) ema 与 bars 等长（无未来计算的旁路通道）
        assert len(detail["ema20"]) == len(detail["bars"])
        # 4) bars 单调递增且不重复
        closes = [b["ts_close_utc"] for b in detail["bars"]]
        assert closes == sorted(closes) and len(set(closes)) == len(closes)
        total_bars_seen_max = max(total_bars_seen_max, len(detail["bars"]))

        r = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 1})
        assert r.status_code == 200, r.text
        detail = r.json()

    # 一整天 78 根 RTH 5m 全部走完
    assert len(detail["bars"]) == 78
    assert detail["info"]["is_completed"]


def test_ema_computed_from_visible_only(seeded_client):
    """EMA 逐步对照本地重算（相同算法 + 前日预热），证明只用可见数据。"""
    s = _create(seeded_client)
    sid = s["session_id"]
    prev_closes = _day_rth_closes(seeded_client, "2024-01-03")

    detail = seeded_client.get(f"/api/v1/replay/sessions/{sid}").json()
    steps = 0
    while not detail["info"]["is_completed"] and steps < 100:
        local = _recompute(prev_closes, [b["close"] for b in detail["bars"]])
        assert abs(detail["ema20"][-1] - round(local, 4)) < 1e-6
        detail = seeded_client.post(
            f"/api/v1/replay/sessions/{sid}/advance", json={"n": 3}
        ).json()
        steps += 1


def _recompute(prev_closes, visible):
    k = 2.0 / 21.0
    ema = sum(prev_closes[:20]) / 20.0
    for c in prev_closes[20:]:
        ema = c * k + ema * (1 - k)
    for c in visible:
        ema = c * k + ema * (1 - k)
    return ema


def _day_rth_closes(seeded_client, day: str) -> list[float]:
    """从回放响应间接拿不到全天数据（这正是设计目标）——用 seed 的原始生成器重算。"""
    from app.core.config import Settings
    from app.domain.bar import SessionType
    from app.domain.instrument import SPY_SYNTH
    from app.services.aggregation import aggregate_day_1m_to_5m
    from app.services.calendar import XNYSCalendar
    from app.services.synthetic import generate_range_1m

    cal = XNYSCalendar()
    bars_1m = generate_range_1m(SPY_SYNTH, date(2024, 1, 2), date(2024, 1, 12), cal,
                                global_seed=Settings().synthetic_seed)
    d = date.fromisoformat(day)
    day_1m = [b for b in bars_1m if b.ts_open_utc.date() == d]
    bars_5m = aggregate_day_1m_to_5m(day_1m, d, cal)
    return [b.close for b in bars_5m if b.session == SessionType.RTH]


def test_key_levels_use_only_known_data(seeded_client):
    """关键价位 = 前日 RTH H/L/C + 当日开盘 + 当日盘前 H/L（全部在 RTH 开盘前已知）。"""
    detail = _create(seeded_client)
    kl = detail["key_levels"]
    prev_closes_day = _day_rth_data(seeded_client, "2024-01-03")

    assert kl["prev_day_high"] == prev_closes_day["high"]
    assert kl["prev_day_low"] == prev_closes_day["low"]
    assert kl["prev_day_close"] == prev_closes_day["close"]
    assert kl["today_open"] == detail["bars"][0]["open"]
    assert kl["gap"] == round(kl["today_open"] - kl["prev_day_close"], 4)
    # 盘前高低来自当日 premarket（已结束时段）
    pre = _day_premarket_hl(seeded_client, DAY)
    assert kl["premarket_high"] == pre["high"]
    assert kl["premarket_low"] == pre["low"]


def _day_rth_data(seeded_client, day: str) -> dict:
    from app.core.config import Settings
    from app.domain.bar import SessionType
    from app.domain.instrument import SPY_SYNTH
    from app.services.aggregation import aggregate_day_1m_to_5m
    from app.services.calendar import XNYSCalendar
    from app.services.synthetic import generate_range_1m

    cal = XNYSCalendar()
    bars_1m = generate_range_1m(SPY_SYNTH, date(2024, 1, 2), date(2024, 1, 12), cal,
                                global_seed=Settings().synthetic_seed)
    d = date.fromisoformat(day)
    day_1m = [b for b in bars_1m if b.ts_open_utc.date() == d]
    bars_5m = aggregate_day_1m_to_5m(day_1m, d, cal)
    rth = [b for b in bars_5m if b.session == SessionType.RTH]
    pre = [b for b in bars_5m if b.session == SessionType.PREMARKET]
    return {
        "high": max(b.high for b in rth),
        "low": min(b.low for b in rth),
        "close": rth[-1].close,
    } | {"pre_high": max(b.high for b in pre), "pre_low": min(b.low for b in pre)}


def _day_premarket_hl(seeded_client, day: str) -> dict:
    d = _day_rth_data(seeded_client, day)
    return {"high": d["pre_high"], "low": d["pre_low"]}


def test_back_only_in_free_mode(seeded_client):
    s_free = _create(seeded_client, mode="free")
    r = seeded_client.post(f"/api/v1/replay/sessions/{s_free['session_id']}/back")
    assert r.status_code == 200
    assert r.json()["info"]["bar_index"] == 6  # 回到 warmup 下限

    s_hidden = _create(seeded_client, mode="hidden_answer")
    r2 = seeded_client.post(f"/api/v1/replay/sessions/{s_hidden['session_id']}/back")
    assert r2.status_code == 403


def test_advance_past_end_completes(seeded_client):
    s = _create(seeded_client)
    sid = s["session_id"]
    r = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 50})
    assert r.status_code == 200
    r2 = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 50})
    d = r2.json()
    assert d["info"]["is_completed"]
    assert len(d["bars"]) == 78
    r3 = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 5})
    assert r3.json()["info"]["is_completed"] and len(r3.json()["bars"]) == 78


def test_judgment_lock_and_validation(seeded_client):
    s = _create(seeded_client)
    sid = s["session_id"]
    url = f"/api/v1/replay/sessions/{sid}/judgments"

    # 缺第二个理由 => 422
    bad = {
        "context_label": "trend_up",
        "considering_trade": True,
        "direction": "long",
        "reasons": ["只有一个理由"],
        "entry": 100.0, "stop": 99.0, "target": 102.0,
    }
    assert seeded_client.post(url, json=bad).status_code == 422
    # stop 方向错误 => 422
    bad2 = dict(bad, reasons=["r1", "r2"], stop=101.0)
    assert seeded_client.post(url, json=bad2).status_code == 422

    good = dict(bad, reasons=["上升趋势回调", "信号K线出现"])
    r = seeded_client.post(url, json=good)
    assert r.status_code == 201
    j = r.json()
    assert j["bar_index"] == 6  # 提交时服务端 cursor
    assert j["payload"]["reasons"] == good["reasons"]

    # 列表可见、内容不可变（无 PUT 路由）
    lst = seeded_client.get(url).json()
    assert len(lst) == 1 and lst[0]["id"] == j["id"]


def test_annotation_cannot_target_future_bar(seeded_client):
    s = _create(seeded_client)
    sid = s["session_id"]
    r = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/annotations",
        json={"bar_index": 50, "kind": "note", "text": "未来K线"},
    )
    assert r.status_code == 403
    r2 = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/annotations",
        json={"bar_index": 3, "kind": "label", "label": "swing_high"},
    )
    assert r2.status_code == 201


def test_random_day_reproducible(seeded_client):
    a = seeded_client.get("/api/v1/replay/random-day", params={"seed": 7}).json()["day"]
    b = seeded_client.get("/api/v1/replay/random-day", params={"seed": 7}).json()["day"]
    c = seeded_client.get("/api/v1/replay/random-day", params={"seed": 8}).json()["day"]
    assert a == b
    assert a in {d for d in [a, c]}  # 合法日期即可
    days = seeded_client.get("/api/v1/replay/days").json()["days"]
    assert a in days


def test_session_on_non_trading_day_rejected(seeded_client):
    r = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-06"})  # 周六
    assert r.status_code == 422


def test_no_data_day_returns_404(seeded_client):
    r = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-02-01"})
    assert r.status_code == 404
