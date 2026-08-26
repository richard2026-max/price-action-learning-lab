from __future__ import annotations

import json

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


def test_markdown_json_response_is_unwrapped_and_references_stay_grounded():
    provider = FakeProvider(
        '```json\n{"source_grounded":"依据","mechanical_approx":"规则",'
        '"coach_interpretation":"诊断","references":["bad"],"insufficient_evidence":"false"}\n```'
    )
    svc = AICoachService(FakeKnowledge(), provider)
    answer = svc.review_decision({"bar_index": 1, "judgment": {"payload": {"context_label": "trend"}}})
    assert answer.source_grounded == "依据"
    assert answer.coach_interpretation == "诊断"
    assert answer.references[0]["book"] == "T"
    assert answer.insufficient_evidence is False


def test_conversational_wrapping_and_string_references_parsed():
    sample = (
        "您好，复盘分析如下：\n```json\n{\n"
        '  "source_grounded": "这是原书依据",\n'
        '  "mechanical_approx": "这是机械近似",\n'
        '  "coach_interpretation": "这是教练解释",\n'
        '  "references": ["T PDF p92: doji定义", "COURSE PDF p647: 缺口说明"],\n'
        '  "insufficient_evidence": false\n'
        "}\n```\n祝您交易顺利！"
    )
    svc = AICoachService(FakeKnowledge(), FakeProvider(sample))
    ans = svc.review_decision({"bar_index": 1, "judgment": {"payload": {"context_label": "trend"}}})
    assert ans.source_grounded == "这是原书依据"
    assert ans.mechanical_approx == "这是机械近似"
    assert ans.coach_interpretation == "这是教练解释"
    assert len(ans.references) == 2
    assert ans.references[0]["book"] == "T"
    assert ans.references[0]["pdf_page"] == 92
    assert ans.references[1]["book"] == "COURSE"
    assert ans.references[1]["pdf_page"] == 647


def test_malformed_json_syntax_recovered_by_regex():
    # 模拟未转义换行或尾随逗号等常见 LLM 语法瑕疵
    malformed = (
        '{\n'
        '  "source_grounded": "下跌趋势中的反弹大多只是回调",\n'
        '  "mechanical_approx": "EMA20 下方运行",\n'
        '  "coach_interpretation": "不宜过早逆势做多",\n'
        '  "insufficient_evidence": true,\n'
        '}'  # 尾随逗号在标准 json.loads 中会报错
    )
    svc = AICoachService(FakeKnowledge(), FakeProvider(malformed))
    ans = svc.review_decision({"bar_index": 1, "judgment": {"payload": {"context_label": "trend"}}})
    assert ans.source_grounded == "下跌趋势中的反弹大多只是回调"
    assert ans.mechanical_approx == "EMA20 下方运行"
    assert ans.coach_interpretation == "不宜过早逆势做多"
    assert ans.insufficient_evidence is True


def test_accidental_recursive_json_is_stripped():
    inner = '{"source_grounded": "真实原书依据", "mechanical_approx": "真实近似", "coach_interpretation": "真实诊断"}'
    wrapped = f'{{"source_grounded": {json.dumps(inner)}, "mechanical_approx": "ok", "coach_interpretation": "ok"}}'
    svc = AICoachService(FakeKnowledge(), FakeProvider(wrapped))
    ans = svc.review_decision({"bar_index": 1, "judgment": {"payload": {"context_label": "trend"}}})
    assert ans.source_grounded == "真实原书依据"


def test_natural_language_section_headers_fallback():
    raw = (
        "【原书依据】趋势中寻找顺势突破点。\n"
        "【系统机械近似】检测到双底形态。\n"
        "【教练解释】此处止损设立偏近，应置于前低下方。"
    )
    svc = AICoachService(FakeKnowledge(), FakeProvider(raw))
    ans = svc.review_decision({"bar_index": 1, "judgment": {"payload": {"context_label": "trend"}}})
    assert "顺势突破点" in ans.source_grounded
    assert "双底" in ans.mechanical_approx
    assert "止损" in ans.coach_interpretation


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
