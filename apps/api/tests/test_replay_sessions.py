"""历史训练会话列表（GET /api/v1/replay/sessions）测试。"""

from __future__ import annotations


def test_list_sessions_empty(seeded_client):
    """未创建任何会话时返回空列表。"""
    resp = seeded_client.get("/api/v1/replay/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_with_judgment_counts(seeded_client):
    """列出会话并正确汇总每条会话的判断条数。"""
    s1 = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"}).json()
    s2 = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-05"}).json()
    assert s1["session_id"] != s2["session_id"]

    # 第一个会话提交 1 条判断
    j = seeded_client.post(
        f"/api/v1/replay/sessions/{s1['session_id']}/judgments",
        json={"context_label": "trading_range", "considering_trade": False},
    ).json()
    assert j["id"] > 0

    rows = seeded_client.get("/api/v1/replay/sessions").json()
    assert len(rows) == 2
    by_id = {r["session_id"]: r for r in rows}
    assert by_id[s1["session_id"]]["judgment_count"] == 1
    assert by_id[s2["session_id"]]["judgment_count"] == 0
    for r in by_id.values():
        assert r["day"] in ("2024-01-04", "2024-01-05")
        assert r["mode"] == "free"
        assert r["provider"] == "synthetic"
        assert r["state"] == "running"
        assert "created_at" in r


def test_list_sessions_limit(seeded_client):
    """limit 参数生效，超范围的取值被 422 拒绝。"""
    for day in ("2024-01-04", "2024-01-05", "2024-01-08"):
        seeded_client.post("/api/v1/replay/sessions", json={"day": day})

    assert len(seeded_client.get("/api/v1/replay/sessions?limit=2").json()) == 2
    assert len(seeded_client.get("/api/v1/replay/sessions?limit=500").json()) == 3
    assert seeded_client.get("/api/v1/replay/sessions?limit=0").status_code == 422
    assert seeded_client.get("/api/v1/replay/sessions?limit=501").status_code == 422