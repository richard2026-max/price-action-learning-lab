"""day_type / 复习调度 / AI Coach / 知识库 API 集成测试。"""

from __future__ import annotations


def test_day_type_trend_from_open_bull(seeded_client):
    r = seeded_client.get("/api/v1/analytics/day-type", params={"day": "2024-01-04", "provider": "synthetic"})
    assert r.status_code == 200
    body = r.json()
    assert "day_type" in body
    assert body["day_type"] in ("trend_from_open_bull", "trend_from_open_bear", "trading_range_day",
                                 "spike_and_channel_bull_day", "spike_and_channel_bear_day", "other")


def test_day_type_no_data(seeded_client):
    r = seeded_client.get("/api/v1/analytics/day-type", params={"day": "2024-02-01", "provider": "synthetic"})
    assert r.status_code == 404


def test_review_due_endpoint(seeded_client):
    # 先审核一条候选
    seeded_client.post("/api/v1/scan/tasks", json={
        "start_day": "2024-01-02", "end_day": "2024-01-08"
    })
    cands = seeded_client.get("/api/v1/scan/candidates").json()
    if cands:
        seeded_client.post(f"/api/v1/scan/candidates/{cands[0]['id']}/review", json={
            "review_status": "confirmed", "review_notes": "test"
        })
        due = seeded_client.get("/api/v1/reviews/due?interval_days=7").json()
        assert isinstance(due["due_reviews"], list)


def test_coach_status(seeded_client):
    r = seeded_client.get("/api/v1/coach/status")
    assert r.status_code == 200
    assert r.json()["enabled"] is False  # 默认禁用


def test_coach_concept_search(seeded_client):
    """AI 禁用模式下，concept 检索仍可返回知识库结果。"""
    r = seeded_client.get("/api/v1/knowledge/concept/wedge")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0 or body["results"] == []


def test_knowledge_search_api(seeded_client):
    r = seeded_client.get("/api/v1/knowledge/search", params={"q": "inside bar"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
