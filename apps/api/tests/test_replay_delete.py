from __future__ import annotations


def test_delete_judgment_and_session_cascades(seeded_client):
    # 1. 创建会话与判断
    created = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"}).json()
    sid = created["session_id"]
    j1 = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/judgments",
        json={"context_label": "trading_range", "considering_trade": False},
    ).json()
    j2 = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/judgments",
        json={"context_label": "trend_up", "considering_trade": False},
    ).json()

    # 确认列表有 2 条判断
    assert len(seeded_client.get(f"/api/v1/replay/sessions/{sid}/judgments").json()) == 2

    # 2. 删除第一条判断
    del_res = seeded_client.delete(f"/api/v1/replay/sessions/{sid}/judgments/{j1['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ok"
    assert del_res.json()["deleted_judgment_id"] == j1["id"]

    # 确认只剩第 2 条
    judgments = seeded_client.get(f"/api/v1/replay/sessions/{sid}/judgments").json()
    assert len(judgments) == 1
    assert judgments[0]["id"] == j2["id"]

    # 重复删除该判断应返回 404
    del_repeat = seeded_client.delete(f"/api/v1/replay/sessions/{sid}/judgments/{j1['id']}")
    assert del_repeat.status_code == 404

    # 3. 删除整场会话
    del_session_res = seeded_client.delete(f"/api/v1/replay/sessions/{sid}")
    assert del_session_res.status_code == 200
    assert del_session_res.json()["status"] == "ok"
    assert del_session_res.json()["deleted_session_id"] == sid

    # 确认会话已被完全删除 (404)
    assert seeded_client.get(f"/api/v1/replay/sessions/{sid}").status_code == 404
