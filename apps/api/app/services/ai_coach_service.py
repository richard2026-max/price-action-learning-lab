"""AI Coach 服务（provider-neutral 抽象，禁用模式可运行）。

约束（PRD §七、brooks-system-design-implications §六）：
- AI 是教练非决策者，不做最终交易判断
- 回答必须区分三类来源：书中定义 / 系统机械近似 / AI 解释
- 无原书依据时明确回答"当前知识库没有足够依据"
- 不泄露未来行情，prompt 不含 cursor 之后数据
- 默认禁用（Settings.ai_enabled=False），禁用时核心功能正常
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services.knowledge_service import KnowledgeService


@dataclass(frozen=True, slots=True)
class CoachAnswer:
    source_grounded: str
    mechanical_approx: str
    coach_interpretation: str
    references: list[dict] = field(default_factory=list)
    insufficient_evidence: bool = False


class LLMProvider(ABC):
    """LLM 提供方抽象接口。"""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class DisabledLLMProvider(LLMProvider):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "AI 功能当前已禁用。"


class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._key = api_key
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import httpx

        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM {resp.status_code}: {resp.text[:200]}")
        return resp.json()["choices"][0]["message"]["content"]


class AICoachService:
    """AI 教练服务：结合知识库检索与 LLM 生成结构化回答。"""

    def __init__(
        self,
        knowledge_svc: KnowledgeService,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self._knowledge = knowledge_svc
        self._llm = llm_provider

    @property
    def enabled(self) -> bool:
        return self._llm is not None

    def ask_concept(self, concept_term: str, question: str = "") -> CoachAnswer:
        refs = self._knowledge.search_by_concept(concept_term, max_results=5)

        if not refs:
            return CoachAnswer(
                source_grounded="",
                mechanical_approx="",
                coach_interpretation="",
                references=[],
                insufficient_evidence=True,
            )

        if not self._llm:
            snippets = "\n---\n".join(
                f"[{r.book_code} PDF p{r.pdf_page}]\n{r.content[:300]}" for r in refs[:3]
            )
            return CoachAnswer(
                source_grounded=f"知识库检索到 {len(refs)} 条相关内容：\n{snippets}",
                mechanical_approx="AI 禁用模式下不生成机械近似说明。",
                coach_interpretation="AI 禁用模式下不生成教练解释。",
                references=[r.to_ref() for r in refs],
            )

        ref_texts = "\n".join(f"[{r.book_code} PDF p{r.pdf_page}] {r.content[:500]}" for r in refs[:3])
        system_prompt = (
            "你是 Al Brooks 价格行为学的学习教练。严格遵循以下规则：\n"
            "1. 仅基于提供的原书片段回答，不编造页码或原意\n"
            "2. 区分三类内容：书中定义 / 系统机械近似 / 你的解释\n"
            "3. 不提供买卖建议，不做最终交易判断\n"
            "4. 依据不足时明确说'知识库没有足够依据'\n"
        )
        user_prompt = f"概念：{concept_term}\n{question}\n\n原书片段：\n{ref_texts}"
        llm_response = self._llm.generate(system_prompt, user_prompt)

        parts = llm_response.split("---")
        return CoachAnswer(
            source_grounded=parts[0].strip() if len(parts) > 0 else "",
            mechanical_approx=parts[1].strip() if len(parts) > 1 else "",
            coach_interpretation=parts[2].strip() if len(parts) > 2 else llm_response,
            references=[r.to_ref() for r in refs],
        )
