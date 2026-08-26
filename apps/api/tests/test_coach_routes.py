def test_coach_config_and_judgment_review_routes_are_available(seeded_client):
    config = seeded_client.get("/api/v1/coach/config")
    assert config.status_code == 200
    assert config.json()["enabled"] is False

    created = seeded_client.post("/api/v1/replay/sessions", json={"day": "2024-01-04", "warmup_bars": 6}).json()
    sid = created["session_id"]
    judgment = seeded_client.post(
        f"/api/v1/replay/sessions/{sid}/judgments",
        json={"context_label": "trading_range", "considering_trade": False},
    ).json()
    reviewed = seeded_client.post(f"/api/v1/coach/sessions/{sid}/judgments/{judgment['id']}/review")
    assert reviewed.status_code == 200
    assert (
        set(("source_grounded", "mechanical_approx", "coach_interpretation", "references", "insufficient_evidence"))
        <= reviewed.json().keys()
    )

    summary = seeded_client.post(f"/api/v1/coach/sessions/{sid}/summary-review")
    assert summary.status_code == 200
    assert len(summary.json()["reviews"]) == 1
