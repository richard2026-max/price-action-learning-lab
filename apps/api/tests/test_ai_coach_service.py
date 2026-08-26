from app.core.config import Settings
from app.services.ai_coach_service import AICoachService, LLMProvider, OpenAICompatProvider
from app.services.knowledge_service import KnowledgeChunk


class FakeKnowledge:
    def search_by_concept(self, term, max_results=5):
        return [KnowledgeChunk("T", 12, None, "Trend pullbacks are entries in a trend.", "c1", "h1")]


class FakeProvider(LLMProvider):
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_no_key_downgrades_without_remote_provider(tmp_path):
    settings = Settings(data_dir=tmp_path, sqlite_path=tmp_path / "a.sqlite", ai_enabled=True, ai_api_key=None)
    svc = AICoachService(FakeKnowledge(), settings=settings)
    assert not svc.enabled
    answer = svc.ask_concept("trend")
    assert "AI 禁用" in answer.coach_interpretation


def test_fake_provider_receives_bounded_review_prompt_and_json_response():
    provider = FakeProvider(
        '{"source_grounded":"book","mechanical_approx":"rules","coach_interpretation":"coach","references":[],"insufficient_evidence":false}'
    )
    svc = AICoachService(FakeKnowledge(), provider)
    context = {
        "session_id": "s",
        "judgment_id": 1,
        "day": "2024-01-04",
        "bar_index": 5,
        "bars": [{"bar_index": 5, "close": 100}],
        "candidates": [{"bar_index": 5}],
        "judgment": {"payload": {"context_label": "trend"}},
        "sim_trades": [{"exit_bar_index": 99, "pnl": 10}],
    }
    answer = svc.review_decision(context)
    assert answer.source_grounded == "book"
    assert len(provider.calls) == 1
    prompt = provider.calls[0][1]
    assert "sim_trades" not in prompt
    assert "严禁推断或引用之后的行情" in prompt


def test_openai_compat_provider_uses_configured_temperature(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def post(*args, **kwargs):
        captured.update(kwargs)
        return Response()

    import httpx

    monkeypatch.setattr(httpx, "post", post)
    OpenAICompatProvider("https://example.test/v1", "key", "model", 0.47).generate("s", "u")
    assert captured["json"]["temperature"] == 0.47
