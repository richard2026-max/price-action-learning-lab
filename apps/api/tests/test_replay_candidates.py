"""Predict First 解锁流程集成测试：候选仅在判断提交后下发。"""

from __future__ import annotations


def _create(seeded_client):
    r = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"})
    assert r.status_code == 200, r.text
    return r.json()


def test_candidates_locked_until_judgment(seeded_client):
    s = _create(seeded_client)
    sid = s["session_id"]

    # 未提交判断：候选为空（Predict First 锁定）
    d0 = seeded_client.get(f"/api/v1/replay/sessions/{sid}").json()
    assert d0["candidates"] == []

    # 提交一个"不交易"判断（解锁）
    r = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/judgments",
        json={"context_label": "trading_range", "considering_trade": False},
    )
    assert r.status_code == 201

    # 解锁后：候选下发，且全部满足 no-lookahead 约束
    d1 = seeded_client.get(f"/api/v1/replay/sessions/{sid}").json()
    assert d1["candidates"], "解锁后候选不应为空"
    cursor_close = d1["bars"][-1]["ts_close_utc"]
    for c in d1["candidates"]:
        assert c["bar_index"] <= d1["info"]["bar_index"]
        assert c["ts_knowable"] <= cursor_close
        assert c["knowable_precision"] == "bar_close"
        assert c["result_type"] in ("boolean", "categorical", "evidence_set")

    ids = {c["detector_id"] for c in d1["candidates"]}
    assert {"bar_anatomy", "doji", "trend_bar", "inside_bar", "outside_bar",
            "signal_bar_evidence"} <= ids

    # 推进后：新 bar 的候选出现（增量可见）
    d2 = seeded_client.post(f"/api/v1/replay/sessions/{sid}/advance", json={"n": 1}).json()
    max_bar = max(c["bar_index"] for c in d2["candidates"])
    assert max_bar == d2["info"]["bar_index"]


def test_detectors_endpoint(seeded_client):
    r = seeded_client.get("/api/v1/detectors")
    assert r.status_code == 200
    body = r.json()
    assert body["profile_version"] == "mvp-c-0.1.0"
    ids = {d["detector_id"] for d in body["detectors"]}
    assert len(ids) == 11  # 7 (MVP-B) + 4 (MVP-C: swing/pullback_leg/hl_counting/trend_lines)
    assert all("spec" in d and "provenance" in d for d in body["detectors"])
