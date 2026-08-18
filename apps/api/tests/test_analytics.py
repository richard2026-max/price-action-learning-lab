"""学习分析与盲测复评（Blind Recheck）测试。"""

from __future__ import annotations


def test_analytics_and_blind_recheck_flow(seeded_client):
    # 1. 创建扫描并生成若干候选
    r = seeded_client.post(
        "/api/v1/scan/tasks",
        json={
            "instrument_id": "SPY",
            "provider": "synthetic",
            "start_day": "2024-01-02",
            "end_day": "2024-01-08",
            "timeframe": "5m",
        },
    )
    assert r.status_code == 201

    cands = seeded_client.get("/api/v1/scan/candidates").json()
    assert len(cands) >= 2

    # 2. 审核候选：一条设为 confirmed，另一条设为 rejected (错题本)
    c1, c2 = cands[0]["id"], cands[1]["id"]
    seeded_client.post(
        f"/api/v1/scan/candidates/{c1}/review",
        json={"review_status": "confirmed", "review_notes": "标准正例", "is_favorite": True},
    )
    seeded_client.post(
        f"/api/v1/scan/candidates/{c2}/review",
        json={
            "review_status": "rejected",
            "rejection_reason": "context_mismatch",
            "review_notes": "背景不符",
            "is_mistake_notebook": True,
        },
    )

    # 3. 提交回放判断
    s = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04"}).json()
    seeded_client.post(
        f"/api/v1/replay/sessions/{s['session_id']}/judgments",
        json={"context_label": "trend_up", "considering_trade": False},
    )

    # 4. 获取 Analytics Overview 概览
    overview = seeded_client.get("/api/v1/analytics/overview").json()
    beh = overview["behavior"]
    assert beh["total_reviewed_candidates"] >= 2
    assert beh["total_confirmed_positives"] >= 1
    assert beh["total_rejected_negatives"] >= 1
    assert beh["total_favorites"] >= 1
    assert beh["total_mistakes"] >= 1
    assert overview["rejections"]["reason_counts"].get("context_mismatch", 0) >= 1

    # 5. 提取盲测复评队列（严格脱敏原始标签）
    queue = seeded_client.get("/api/v1/analytics/recheck-queue").json()
    assert len(queue) >= 2
    assert all("review_status" not in item for item in queue)

    # 6. 提交盲测复评结论
    recheck_res = seeded_client.post(
        "/api/v1/analytics/recheck",
        json={"candidate_id": c1, "recheck_status": "confirmed", "recheck_notes": "再次确认是正例"},
    ).json()
    assert recheck_res["candidate_id"] == c1
    assert recheck_res["original_status"] == "confirmed"
    assert recheck_res["is_consistent"] is True

    # 提交一个不一致的复评
    recheck_inconsistent = seeded_client.post(
        "/api/v1/analytics/recheck",
        json={"candidate_id": c2, "recheck_status": "confirmed", "recheck_notes": "改判了"},
    ).json()
    assert recheck_inconsistent["candidate_id"] == c2
    assert recheck_inconsistent["original_status"] == "rejected"
    assert recheck_inconsistent["is_consistent"] is False
