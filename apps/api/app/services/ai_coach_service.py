"""AI 教练服务：知识库 grounding、判断复盘和安全降级。"""

from __future__ import annotations

import json
import re
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
        import time

        import httpx

        max_retries = 3
        for attempt in range(max_retries):
            resp = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": self._temperature,
                },
                timeout=60,
            )
            if resp.status_code == 429 and attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            if resp.status_code != 200:
                raise RuntimeError(f"LLM {resp.status_code}: {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        raise RuntimeError("LLM 429: 模型调用并发频率超限，请稍候重试")


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
        self._review_cache: dict[tuple[str, int], CoachAnswer] = {}
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

    def evict_review(self, session_id: str, judgment_id: int) -> None:
        """清除指定判断的 AI 复盘内存缓存。"""
        self._review_cache.pop((session_id, judgment_id), None)

    def evict_session(self, session_id: str) -> None:
        """清除整场会话的全部 AI 复盘内存缓存。"""
        keys_to_del = [k for k in self._review_cache if k[0] == session_id]
        for k in keys_to_del:
            self._review_cache.pop(k, None)

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

    def review_decision(
        self, context: dict[str, Any], force_refresh: bool = False
    ) -> CoachAnswer:
        """复盘一个已提交判断；默认返回缓存结果，force_refresh=True 时强制重跑。"""
        session_id = str(context.get("session_id", ""))
        judgment_id = int(context.get("judgment_id", 0))
        cache_key = (session_id, judgment_id)
        if not force_refresh and session_id and judgment_id and cache_key in self._review_cache:
            return self._review_cache[cache_key]

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
        try:
            response = self._llm.generate(self._system_prompt() + "\n" + self._review_rules(), prompt)
            answer = self._answer_from_text(response, refs)
            if session_id and judgment_id:
                self._review_cache[cache_key] = answer
            return answer
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                diag = "模型接口并发频率受限 (429 Rate Limit)，请稍候 2 秒后点击右上角「🔄 重新分析」重试。"
            else:
                diag = f"AI 服务暂不可用 ({err_msg[:120]})，请稍候点击「🔄 重新分析」。"
            return CoachAnswer(
                source_grounded="当前远程分析暂未就绪，已保留本地知识库相关依据。",
                mechanical_approx="已保留判断时点可见的客观事实与价格形态。",
                coach_interpretation=diag,
                references=[r.to_ref() for r in refs],
                insufficient_evidence=True,
            )

    # Compatibility aliases for callers using review terminology.
    review_judgment = review_decision

    def summary_review(self, contexts: list[dict[str, Any]]) -> dict[str, Any]:
        return {"reviews": [self.review_decision(c) for c in contexts]}

    @staticmethod
    def decision_review_prompt(context: dict[str, Any], references: str = "") -> str:
        return (
            "请作为专业价格行为学教练，对该时点的学员决策进行深度对照复盘。\n"
            "【强制输出约束】：\n"
            "1. 必须全程使用中文回答。\n"
            "2. 只能基于当时可见行情与事实，严禁推断或引用之后的行情、未来数据或后验交易盈亏。\n"
            "3. 必须直接输出合法标准 JSON 对象，严禁使用 ```json 或 ``` 代码块包裹，首字符必须是 {，末字符必须是 }。\n"
            "4. JSON 对象必须且只能包含以下 5 个字段：\n"
            "   - \"source_grounded\": 纯文本字符串。对照阿布价格行为学课件原意（严禁包含未解析 JSON 或代码块）。\n"
            "   - \"mechanical_approx\": 纯文本字符串。当前行情客观事实与技术形态分析。\n"
            "   - \"coach_interpretation\": 纯文本字符串。针对学员方向、理由、止损与目标的教练诊断与思维纠偏。\n"
            '   - "references": 数组。每项为 {"book": "T/R/REV/COURSE", '
            '"pdf_page": 数字页码, "content": "要点摘要"}。\n'
            '   - "insufficient_evidence": 布尔值（true 或 false）。\n\n'
            f"判断时点可见上下文：{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}\n"
            f"知识库检索片段：{references}"
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是 Al Brooks 价格行为学习教练。严格使用专业中文术语，只教练不带单，"
            "不做最终交易决定；不编造页码或原意。"
        )

    @staticmethod
    def _review_rules() -> str:
        return (
            "必须清晰区分三层：阿布价格行为学课件原意、当前行情客观事实、教练解释；"
            "依据不足时明确标记 insufficient_evidence 为 true。"
        )

    @staticmethod
    def _answer_from_text(text: str, refs: list[Any]) -> CoachAnswer:
        """多重容错解析：剥除代码块、正则容错提取核心字段、支持自然语言分段与引用结构化转换。"""
        clean = text.strip()
        # 1. 剥离可能存在的 ```json ... ``` 标记
        fence_match = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", clean)
        if fence_match:
            clean = fence_match.group(1).strip()
        if not clean.startswith("{") and "{" in clean and "}" in clean:
            first_b = clean.find("{")
            last_b = clean.rfind("}")
            if first_b < last_b:
                clean = clean[first_b : last_b + 1].strip()

        obj: dict[str, Any] | None = None
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                obj = parsed
        except (ValueError, TypeError):
            obj = None

        # 2. 正则兜底提取字段（应对未转义双引号、换行符导致的语法解析错误）
        if obj is None:
            obj = AICoachService._regex_extract_fields(text)

        # 3. 若成功提取到核心字段
        if obj and any(k in obj for k in ("source_grounded", "mechanical_approx", "coach_interpretation")):
            sg = AICoachService._strip_field_wrapper(str(obj.get("source_grounded", "")), "source_grounded")
            ma = AICoachService._strip_field_wrapper(str(obj.get("mechanical_approx", "")), "mechanical_approx")
            ci = AICoachService._strip_field_wrapper(str(obj.get("coach_interpretation", "")), "coach_interpretation")

            references = AICoachService._parse_references(obj.get("references"), refs)
            flag = obj.get("insufficient_evidence", False)
            insufficient = flag if isinstance(flag, bool) else str(flag).lower() in ("true", "1", "yes")

            return CoachAnswer(
                source_grounded=sg,
                mechanical_approx=ma,
                coach_interpretation=ci,
                references=references,
                insufficient_evidence=insufficient,
            )

        # 4. 自然语言标志分段兜底（如模型输出【原书依据】...【系统机械近似】...）
        return AICoachService._parse_section_fallback(text, refs)

    @staticmethod
    def _strip_field_wrapper(val: str, field_key: str) -> str:
        """剥离字段内意外包含的外层 JSON 或代码块。"""
        s = val.strip()
        if "```" in s:
            m = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", s)
            if m:
                s = m.group(1).strip()
        if s.startswith("{") and f'"{field_key}"' in s:
            try:
                inner = json.loads(s)
                if isinstance(inner, dict) and field_key in inner:
                    return str(inner[field_key]).strip()
            except Exception:
                pass
        return s

    @staticmethod
    def _regex_extract_fields(raw: str) -> dict[str, Any]:
        """正则容错抽取 JSON 核心字段。"""
        fields: dict[str, Any] = {}
        for key in ("source_grounded", "mechanical_approx", "coach_interpretation"):
            m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
            if m:
                val = m.group(1)
                try:
                    fields[key] = json.loads(f'"{val}"')
                except Exception:
                    fields[key] = val.replace('\\"', '"').replace("\\n", "\n")
        m_ie = re.search(r'"insufficient_evidence"\s*:\s*(true|false|"[^"]*")', raw, re.IGNORECASE)
        if m_ie:
            fields["insufficient_evidence"] = "true" in m_ie.group(1).lower()
        return fields

    @staticmethod
    def _parse_references(model_refs: Any, default_refs: list[Any]) -> list[dict[str, Any]]:
        """将模型返回的字符串或字典列表统一解析为结构化引用。"""
        out: list[dict[str, Any]] = []
        if isinstance(model_refs, list):
            for item in model_refs:
                if isinstance(item, dict):
                    page_val = item.get("pdf_page", 0)
                    page_num = int(page_val) if str(page_val).isdigit() else 0
                    out.append({
                        "book": str(item.get("book", "参考资料")),
                        "pdf_page": page_num,
                        "print_page": item.get("print_page"),
                        "source_file": str(item.get("source_file", "")),
                        "source_type": str(item.get("source_type", "book_pdf")),
                        "content": str(item.get("content") or item.get("quote") or ""),
                    })
                elif isinstance(item, str) and item.strip():
                    m = re.search(r"(?:\[)?([A-Za-z0-9_]+)\s+PDF\s+p\.?(\d+)(?:\])?(?:\s*[:：]\s*(.*))?", item)
                    if m:
                        code = m.group(1).upper()
                        page = int(m.group(2))
                        desc = (m.group(3) or item).strip()
                        out.append({
                            "book": code,
                            "pdf_page": page,
                            "print_page": None,
                            "source_type": "book_pdf" if code in ("T", "R", "REV", "BOOK") else "courseware",
                            "source_file": "",
                            "content": desc,
                        })
        if not out and default_refs:
            return [r.to_ref() for r in default_refs]
        return out

    @staticmethod
    def _parse_section_fallback(text: str, refs: list[Any]) -> CoachAnswer:
        """处理自然语言或标志符分段。"""
        clean = text.strip()
        if "---" in clean:
            parts = clean.split("---")
            return CoachAnswer(
                parts[0].strip(),
                parts[1].strip() if len(parts) > 1 else "",
                parts[2].strip() if len(parts) > 2 else clean,
                [r.to_ref() for r in refs],
            )
        p1 = re.search(
            r"【(?:阿布价格行为学课件原意|课件原意|原书依据|理论依据)】|(?:课件原意|原书依据)\s*[:：]",
            clean,
        )
        p2 = re.search(
            r"【(?:当前行情客观事实|行情客观事实|系统机械近似|机械近似)】|(?:行情客观事实|机械近似)\s*[:：]",
            clean,
        )
        p3 = re.search(r"【(?:教练解释|学员诊断)】|教练解释\s*[:：]", clean)
        if p1 and p2 and p3:
            s1 = clean[p1.end() : p2.start()].strip()
            s2 = clean[p2.end() : p3.start()].strip()
            s3 = clean[p3.end() :].strip()
            return CoachAnswer(s1, s2, s3, [r.to_ref() for r in refs])

        # 终极兜底：剥除任何反引号代码块，绝不输出 raw json 格式
        clean = re.sub(r"```(?:json|JSON)?", "", clean).replace("```", "").strip()
        return CoachAnswer(
            clean,
            "未检测到独立机械近似分段。",
            "已合并至依据区。",
            [r.to_ref() for r in refs],
        )

