"""AI 教练服务：知识库 grounding、判断复盘和安全降级。"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.services.knowledge_service import KnowledgeService


@dataclass(frozen=True, slots=True)
class CoachAnswer:
    source_grounded: str
    mechanical_approx: str
    coach_interpretation: str
    references: list[dict] = field(default_factory=list)
    insufficient_evidence: bool = False


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class DisabledLLMProvider(LLMProvider):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "AI 功能当前已禁用。"


class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str, ai_temperature: float = 0.2) -> None:
        self._base_url = base_url.rstrip("/")
        self._key = api_key
        self._model = model
        self._temperature = ai_temperature

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import httpx

        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "temperature": self._temperature,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM {resp.status_code}: {resp.text[:200]}")
        return resp.json()["choices"][0]["message"]["content"]


class AICoachService:
    def __init__(
        self,
        knowledge_svc: KnowledgeService,
        llm_provider: LLMProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._knowledge = knowledge_svc
        self._settings = settings or Settings()
        self._injected_provider = llm_provider is not None
        self._llm: LLMProvider | None = None
        # An injected provider is intentionally useful for tests/local adapters. Remote
        # DeepSeek is constructed only when both the feature flag and key are present.
        if llm_provider is not None:
            self._llm = llm_provider
        elif self._settings.ai_enabled and self._settings.ai_api_key:
            self._llm = OpenAICompatProvider(
                self._settings.ai_base_url,
                self._settings.ai_api_key,
                self._settings.ai_model,
                self._settings.ai_temperature,
            )
        else:
            self._llm = None

    @property
    def enabled(self) -> bool:
        return self._injected_provider or (
            self._llm is not None and self._settings.ai_enabled and bool(self._settings.ai_api_key)
        )

    def config(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": bool(self._settings.ai_api_key),
            "provider": "deepseek"
            if self._settings.ai_base_url.startswith("https://api.deepseek.com")
            else "openai-compatible",
            "model": self._settings.ai_model,
            "temperature": self._settings.ai_temperature,
        }

    def ask_concept(self, concept_term: str, question: str = "") -> CoachAnswer:
        refs = self._knowledge.search_by_concept(concept_term, max_results=5)
        if not refs:
            return CoachAnswer("", "", "", [], True)
        if not self._llm or not self.enabled:
            snippets = "\n---\n".join(f"[{r.book_code} PDF p{r.pdf_page}]\n{r.content[:300]}" for r in refs[:3])
            return CoachAnswer(
                f"知识库检索到 {len(refs)} 条相关内容：\n{snippets}",
                "AI 禁用模式下不生成机械近似说明。",
                "AI 禁用模式下不生成教练解释。",
                [r.to_ref() for r in refs],
            )
        ref_texts = "\n".join(f"[{r.book_code} PDF p{r.pdf_page}] {r.content[:500]}" for r in refs[:3])
        response = self._llm.generate(
            self._system_prompt(), f"概念：{concept_term}\n{question}\n\n原书片段：\n{ref_texts}"
        )
        return self._answer_from_text(response, refs)

    def review_decision(self, context: dict[str, Any]) -> CoachAnswer:
        """复盘一个已提交判断；context 已由 extractor 按判断边界裁剪。"""
        query = str(context.get("judgment", {}).get("payload", {}))
        search = getattr(self._knowledge, "search", self._knowledge.search_by_concept)
        refs = search(query, max_results=5)
        # Never send posterior trades or any unbounded fields to an LLM.
        safe_context = {
            k: context.get(k)
            for k in (
                "session_id",
                "judgment_id",
                "day",
                "bar_index",
                "bars",
                "ema20",
                "key_levels",
                "candidates",
                "judgment",
            )
        }
        safe_context["candidates"] = [
            c for c in (safe_context.get("candidates") or []) if c.get("bar_index", 0) <= safe_context["bar_index"]
        ]
        if not self._llm or not self.enabled:
            return CoachAnswer(
                source_grounded="知识库没有足够依据，或 AI 未配置。",
                mechanical_approx="已保留判断时刻的机械上下文；未调用远程模型。",
                coach_interpretation="请依据当时可见的 K 线和规则自行复盘。",
                references=[r.to_ref() for r in refs],
                insufficient_evidence=not bool(refs),
            )
        ref_text = (
            "\n".join(f"[{r.book_code} PDF p{r.pdf_page}] {r.content[:500]}" for r in refs[:3]) or "（无匹配原书片段）"
        )
        prompt = self.decision_review_prompt(safe_context, ref_text)
        response = self._llm.generate(self._system_prompt() + "\n" + self._review_rules(), prompt)
        return self._answer_from_text(response, refs)

    # Compatibility aliases for callers using review terminology.
    review_judgment = review_decision

    def summary_review(self, contexts: list[dict[str, Any]]) -> dict[str, Any]:
        return {"reviews": [self.review_decision(c) for c in contexts]}

    @staticmethod
    def decision_review_prompt(context: dict[str, Any], references: str = "") -> str:
        return (
            "执行判断复盘。以下 JSON 只包含提交判断时已经可见的信息；严禁推断或引用之后的行情、交易结果或未来数据。\n"
            "请严格输出 JSON 对象，字段必须为 source_grounded、mechanical_approx、"
            "coach_interpretation、references、insufficient_evidence。"
            "前三个字段为字符串，references 为数组，insufficient_evidence 为布尔值。\n"
            f"判断上下文：{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}\n"
            f"知识库片段：{references}"
        )

    @staticmethod
    def _system_prompt() -> str:
        return "你是 Al Brooks 价格行为学习教练。只教练，不做最终交易决定；不编造页码或原意。"

    @staticmethod
    def _review_rules() -> str:
        return "来源必须分成：原书依据、系统机械近似、教练解释；依据不足时明确标记 insufficient_evidence。"

    @staticmethod
    def _answer_from_text(text: str, refs: list[Any]) -> CoachAnswer:
        """解析纯 JSON、```json``` 代码块及带前后说明的 JSON。"""
        candidate = text.strip()
        if "```" in candidate:
            blocks = candidate.split("```")
            candidate = next((block.strip() for block in blocks if block.strip().startswith("{")), candidate)
        if not candidate.startswith("{") and "{" in candidate and "}" in candidate:
            candidate = candidate[candidate.find("{") : candidate.rfind("}") + 1]
        try:
            obj = json.loads(candidate)
            model_refs = obj.get("references")
            valid_model_refs = isinstance(model_refs, list) and all(
                isinstance(item, dict) for item in model_refs
            )
            references = model_refs if valid_model_refs else [r.to_ref() for r in refs]
            flag = obj.get("insufficient_evidence", False)
            insufficient = flag if isinstance(flag, bool) else str(flag).lower() == "true"
            return CoachAnswer(
                str(obj.get("source_grounded", "")),
                str(obj.get("mechanical_approx", "")),
                str(obj.get("coach_interpretation", "")),
                references,
                insufficient,
            )
        except (ValueError, TypeError):
            parts = text.split("---")
            return CoachAnswer(
                parts[0].strip(),
                parts[1].strip() if len(parts) > 1 else "",
                parts[2].strip() if len(parts) > 2 else text,
                [r.to_ref() for r in refs],
            )
