"""DecisionContextExtractor 的 no-lookahead 聚焦测试。"""

from datetime import datetime

from app.domain.instrument import SPY_SYNTH
from app.services.decision_review_service import DecisionContextExtractor


def test_extract_uses_judgment_boundary_not_later_cursor(seeded_client):
    created = seeded_client.post(
        "/api/v1/replay/sessions", json={"day": "2024-01-04", "warmup_bars": 6}
    ).json()
    session_id = created["session_id"]
    judgment = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/judgments",
        json={"context_label": "trading_range", "considering_trade": False},
    ).json()

    # Move the live session well past the judgment. The review must not follow it.
    later = seeded_client.post(
        f"/api/v1/replay/sessions/{session_id}/advance", json={"n": 10}
    ).json()
    assert later["info"]["bar_index"] > judgment["bar_index"]

    app = seeded_client.app
    extractor = DecisionContextExtractor(
        replay_service=app.state.replay_service,
        trade_repo=app.state.sim_trade_service._repo,
    )
    context = extractor.extract(session_id, judgment["id"], SPY_SYNTH)

    assert context["bar_index"] == judgment["bar_index"]
    assert len(context["bars"]) <= 30
    judgment_time = datetime.fromisoformat(judgment["bar_time_utc"])
    last_bar_time = datetime.fromisoformat(context["bars"][-1]["ts_close_utc"])
    assert last_bar_time == judgment_time.replace(tzinfo=last_bar_time.tzinfo)
    assert all(c["bar_index"] <= judgment["bar_index"] for c in context["candidates"])
    assert all(
        datetime.fromisoformat(c["ts_knowable"]) <= last_bar_time
        for c in context["candidates"]
    )
    assert context["judgment"]["id"] == judgment["id"]
    assert context["judgment"]["payload"] == judgment["payload"]
