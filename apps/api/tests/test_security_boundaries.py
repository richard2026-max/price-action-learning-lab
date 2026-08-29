"""安全边界回归：Scanner/Analytics/Coach 的用户隔离、运维接口生产禁用与启动守卫。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _login(client, subject: str) -> str:
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"subject": subject, "display_name": subject},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_scan_task(client, token: str) -> str:
    response = client.post(
        "/api/v1/scan/tasks",
        json={
            "instrument_id": "SPY",
            "provider": "synthetic",
            "start_day": "2024-01-02",
            "end_day": "2024-01-08",
            "timeframe": "5m",
        },
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_scanner_tasks_and_candidates_are_isolated_by_user(seeded_client):
    token_a = _login(seeded_client, "scan-a")
    token_b = _login(seeded_client, "scan-b")

    task_id = _create_scan_task(seeded_client, token_a)

    tasks_b = seeded_client.get("/api/v1/scan/tasks", headers=_headers(token_b))
    assert tasks_b.status_code == 200
    assert all(t["id"] != task_id for t in tasks_b.json())

    task_b_view = seeded_client.get(f"/api/v1/scan/tasks/{task_id}", headers=_headers(token_b))
    assert task_b_view.status_code == 404

    candidates_b = seeded_client.get("/api/v1/scan/candidates", headers=_headers(token_b))
    assert candidates_b.status_code == 200
    assert all(c["task_id"] != task_id for c in candidates_b.json())

    candidate_id = seeded_client.get(
        "/api/v1/scan/candidates", headers=_headers(token_a)
    ).json()[0]["id"]
    review = seeded_client.post(
        f"/api/v1/scan/candidates/{candidate_id}/review",
        json={"review_status": "confirmed"},
        headers=_headers(token_b),
    )
    assert review.status_code == 404


def test_analytics_overview_and_trade_stats_are_per_user(seeded_client):
    token_a = _login(seeded_client, "stat-a")
    token_b = _login(seeded_client, "stat-b")

    created = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": "2024-01-04"},
        headers=_headers(token_a),
    )
    assert created.status_code == 200, created.text
    judgment = seeded_client.post(
        f"/api/v1/replay/sessions/{created.json()['session_id']}/judgments",
        json={
            "context_label": "trend_up",
            "considering_trade": False,
            "direction": "none",
        },
        headers=_headers(token_a),
    )
    assert judgment.status_code == 201, judgment.text

    overview_a = seeded_client.get("/api/v1/analytics/overview", headers=_headers(token_a)).json()
    overview_b = seeded_client.get("/api/v1/analytics/overview", headers=_headers(token_b)).json()
    assert overview_a["behavior"]["total_sessions"] == 1
    assert overview_a["behavior"]["total_judgments"] == 1
    assert overview_b["behavior"]["total_sessions"] == 0
    assert overview_b["behavior"]["total_judgments"] == 0

    trades_a = seeded_client.get("/api/v1/analytics/trade-stats", headers=_headers(token_a))
    trades_b = seeded_client.get("/api/v1/analytics/trade-stats", headers=_headers(token_b))
    assert trades_a.status_code == 200 and trades_b.status_code == 200
    assert trades_b.json()["total_trades"] == 0


def test_coach_review_requires_session_ownership(seeded_client):
    token_a = _login(seeded_client, "coach-a")
    token_b = _login(seeded_client, "coach-b")

    created = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": "2024-01-04"},
        headers=_headers(token_a),
    ).json()
    session_id = created["session_id"]
    judgment = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/judgments",
        json={
            "context_label": "trading_range",
            "considering_trade": False,
            "direction": "none",
        },
        headers=_headers(token_a),
    ).json()

    foreign = seeded_client.post(
        f"/api/v1/coach/sessions/{session_id}/judgments/{judgment['id']}/review",
        headers=_headers(token_b),
    )
    assert foreign.status_code == 404

    own = seeded_client.post(
        f"/api/v1/coach/sessions/{session_id}/judgments/{judgment['id']}/review",
        headers=_headers(token_a),
    )
    assert own.status_code == 200


def test_data_seed_blocked_in_production_mode(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sqlite_path=tmp_path / "app.sqlite",
        debug=False,
        auth_token_secret="test-secret",
        legacy_local_user_enabled=False,
        ai_enabled=False,
        ai_api_key=None,
    )
    client = TestClient(create_app(settings))
    response = client.post("/api/v1/data/seed", json={"start": "2024-01-02", "end": "2024-01-03"})
    assert response.status_code == 403


def test_production_without_token_secret_refuses_to_start(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        sqlite_path=tmp_path / "app.sqlite",
        debug=False,
        auth_token_secret=None,
    )
    with pytest.raises(RuntimeError, match="PALL_AUTH_TOKEN_SECRET"):
        create_app(settings)
