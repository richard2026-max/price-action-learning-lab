"""Scanner 扫描任务执行与候选人工审核端到端测试（MVP-D）。"""

from __future__ import annotations


def test_scanner_full_workflow(seeded_client):
    # 1. 创建扫描任务（扫描 2024-01-02 ~ 2024-01-12 内所有已注册 detector）
    r = seeded_client.post(
        "/api/v1/scan/tasks",
        json={
            "instrument_id": "SPY",
            "provider": "synthetic",
            "start_day": "2024-01-02",
            "end_day": "2024-01-12",
            "timeframe": "5m",
            "detector_ids": [],  # 全量
        },
    )
    assert r.status_code == 201, r.text
    task = r.json()
    task_id = task["id"]
    assert task["status"] == "completed"
    assert task["progress"] == 1.0
    assert task["scanned_days"] > 0
    assert task["candidate_count"] > 0

    # 2. 查询任务详情与任务列表
    t_detail = seeded_client.get(f"/api/v1/scan/tasks/{task_id}").json()
    assert t_detail["id"] == task_id
    t_list = seeded_client.get("/api/v1/scan/tasks").json()
    assert any(t["id"] == task_id for t in t_list)

    # 3. 按条件筛选候选（如 inside_bar）
    cands = seeded_client.get(
        "/api/v1/scan/candidates",
        params={"task_id": task_id, "detector_id": "inside_bar"},
    ).json()
    assert len(cands) > 0
    cand_id = cands[0]["id"]
    assert cands[0]["detector_id"] == "inside_bar"
    assert cands[0]["review_status"] == "unreviewed"

    # 4. 人工审核候选（标记为 confirmed 并加星收藏）
    rev_ok = seeded_client.post(
        f"/api/v1/scan/candidates/{cand_id}/review",
        json={
            "review_status": "confirmed",
            "review_notes": "标准内包线，位于EMA20支撑处",
            "is_favorite": True,
        },
    )
    assert rev_ok.status_code == 200
    c_updated = rev_ok.json()
    assert c_updated["review_status"] == "confirmed"
    assert c_updated["is_favorite"] is True
    assert c_updated["reviewed_at"] is not None

    # 5. 过滤查询收藏与审核状态
    favs = seeded_client.get("/api/v1/scan/candidates", params={"only_favorites": True}).json()
    assert any(c["id"] == cand_id for c in favs)

    # 6. 人工拒绝并记录原因（如 context_mismatch 并加入错题本）
    cand_id2 = cands[1]["id"]
    rev_rej = seeded_client.post(
        f"/api/v1/scan/candidates/{cand_id2}/review",
        json={
            "review_status": "rejected",
            "rejection_reason": "context_mismatch",
            "review_notes": "背景为强单边行情，不能作逆势突破看",
            "is_mistake_notebook": True,
        },
    )
    assert rev_rej.status_code == 200
    c_rej = rev_rej.json()
    assert c_rej["review_status"] == "rejected"
    assert c_rej["rejection_reason"] == "context_mismatch"
    assert c_rej["is_mistake_notebook"] is True

    # 7. 过滤错题本
    mistakes = seeded_client.get("/api/v1/scan/candidates", params={"only_mistakes": True}).json()
    assert any(c["id"] == cand_id2 for c in mistakes)
