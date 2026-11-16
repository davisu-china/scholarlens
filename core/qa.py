"""快速问答服务（PRD F2）：路由 → 混合检索 → 受约束生成(流式) → 引用校验。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from core.agent.coordinator import enumerate_evidence
from core.domain import Evidence, Query, VerifiedAnswer
from core.llm import prompts
from core.ports import LLMClient
from core.retrieval.hybrid import HybridRetriever
from core.retrieval.router import classify_rule
from core.verify.citation import CitationVerifier


@dataclass
class QAResult:
    answer: VerifiedAnswer
    evidence: dict[str, Evidence]


class QAService:
    def __init__(
        self,
        *,
        llm: LLMClient,
        retriever: HybridRetriever,
        verifier: CitationVerifier,
        model: str | None = None,
        min_evidence: int = 1,
        min_score: float = 0.0,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._verifier = verifier
        self._model = model
        self._min_evidence = min_evidence
        self._min_score = min_score

    async def _retrieve(self, question: str, filters: dict) -> dict[str, Evidence]:
        intent = classify_rule(question)
        hits = await self._retriever.retrieve(Query(text=question, intent=intent, filters=filters))
        # 低于分数阈值的证据视为不相关（证据不足 → 拒答，不编造）
        hits = [h for h in hits if h.score > self._min_score]
        return {eid: ev for eid, ev in enumerate_evidence(hits)}

    async def answer(self, question: str, *, filters: dict | None = None) -> QAResult:
        """非流式：一次性返回校验后的答案。"""
        evidence = await self._retrieve(question, filters or {})
        if len(evidence) < self._min_evidence:
            # 证据不足时拒答，不编造（PRD F2）
            return QAResult(
                answer=VerifiedAnswer(answer="根据现有文献，没有找到足以回答该问题的证据。", trust=1.0),
                evidence={},
            )
        draft = await self._llm.complete(
            prompts.QA_PROMPT.format(question=question, evidence=prompts.format_evidence(evidence)),
            model=self._model,
            system=prompts.QA_SYSTEM_PROMPT,
        )
        verified = await self._verifier.verify(draft, evidence)
        return QAResult(answer=verified, evidence=evidence)

    async def stream(self, question: str, *, filters: dict | None = None) -> AsyncIterator[dict]:
        """流式：先吐 token，最后吐一次校验结果。供 /query 的 SSE 使用。"""
        evidence = await self._retrieve(question, filters or {})
        if len(evidence) < self._min_evidence:
            yield {"event": "token", "data": "根据现有文献，没有找到足以回答该问题的证据。"}
            yield {"event": "done", "data": {"trust": 1.0, "claims": []}}
            return

        parts: list[str] = []
        async for tok in self._llm.stream(
            prompts.QA_PROMPT.format(question=question, evidence=prompts.format_evidence(evidence)),
            model=self._model,
            system=prompts.QA_SYSTEM_PROMPT,
        ):
            parts.append(tok)
            yield {"event": "token", "data": tok}

        verified = await self._verifier.verify("".join(parts), evidence)
        yield {
            "event": "done",
            "data": {
                "trust": verified.trust,
                "claims": [c.model_dump() for c in verified.claims],
                "evidence": {eid: ev.model_dump() for eid, ev in evidence.items()},
            },
        }
