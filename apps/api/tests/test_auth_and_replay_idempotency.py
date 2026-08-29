"""小程序接入所需的认证、资源隔离和移动网络幂等回归测试。"""


def _login(client, subject: str) -> str:
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"subject": subject, "display_name": subject},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_replay_sessions_are_isolated_by_user(seeded_client):
    token_a = _login(seeded_client, "user-a")
    token_b = _login(seeded_client, "user-b")

    created = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": "2024-01-04"},
        headers=_headers(token_a),
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    own = seeded_client.get(
        f"/api/v1/replay/sessions/{session_id}",
        headers=_headers(token_a),
    )
    foreign = seeded_client.get(
        f"/api/v1/replay/sessions/{session_id}",
        headers=_headers(token_b),
    )
    assert own.status_code == 200
    assert foreign.status_code == 404


def test_advance_request_is_idempotent_and_versioned(seeded_client):
    token = _login(seeded_client, "advance-user")
    created = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": "2024-01-04"},
        headers=_headers(token),
    ).json()
    session_id = created["session_id"]
    version = created["info"]["cursor_version"]
    payload = {"n": 1, "expected_cursor_version": version, "request_id": "advance-001"}

    first = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/advance",
        json=payload,
        headers=_headers(token),
    )
    repeated = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/advance",
        json=payload,
        headers=_headers(token),
    )
    assert first.status_code == 200, first.text
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["info"]["bar_index"] == first.json()["info"]["bar_index"]
    assert repeated.json()["info"]["cursor_version"] == first.json()["info"]["cursor_version"]

    mismatch = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/advance",
        json={**payload, "n": 2},
        headers=_headers(token),
    )
    assert mismatch.status_code == 409


def test_judgment_client_request_id_prevents_duplicates(seeded_client):
    token = _login(seeded_client, "judgment-user")
    created = seeded_client.post(
        "/api/v1/replay/sessions",
        json={"day": "2024-01-04"},
        headers=_headers(token),
    ).json()
    payload = {
        "client_request_id": "judgment-001",
        "context_label": "trend_up",
        "considering_trade": True,
        "direction": "long",
        "reasons": ["趋势回调", "强信号棒"],
        "entry": 100.0,
        "stop": 99.0,
        "target": 102.0,
    }
    url = f"/api/v1/replay/sessions/{created['session_id']}/judgments"
    first = seeded_client.post(url, json=payload, headers=_headers(token))
    repeated = seeded_client.post(url, json=payload, headers=_headers(token))
    assert first.status_code == 201, first.text
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == first.json()["id"]
