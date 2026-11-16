"""引用校验与反幻觉（PRD 第 11 章）—— 本项目最核心的差异点。

普通 RAG 只「让模型带引用」；这里在生成之后逐句验证每条引用是否成立：
  1. 受约束生成要求每句以 [eid] 结尾（此处做合法性解析）
  2. 切成「论断 + 引用」对
  3. NLI 判定 P(证据蕴含论断)；数值类额外做规则校验
  4. 低于阈值的句子交 LLM 依据证据重写一次
  5. 在证据内定位最相似句子的 provenance，供前端精确高亮
"""

from __future__ import annotations

import re

from core.domain import Claim, Evidence, VerifiedAnswer
from core.ports import LLMClient, NLIModel

# 句尾引用：支持 [e1] 或 [e1][e2] 或 [e1, e2]
_CITE = re.compile(r"\[([a-zA-Z0-9_\-, ]+)\]")
# 句子切分：中英文句末标点
_SENT_SPLIT = re.compile(r"(?<=[。！？.!?])\s*")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def split_claims(answer: str) -> list[Claim]:
    """把答案切成 (论断, [eid...]) 列表。无引用的句子 eids 为空。"""
    claims: list[Claim] = []
    for raw in _SENT_SPLIT.split(answer.strip()):
        sent = raw.strip()
        if not sent:
            continue
        eids: list[str] = []
        for m in _CITE.findall(sent):
            eids.extend(e.strip() for e in m.split(",") if e.strip())
        text = _CITE.sub("", sent).strip()
        if text:
            claims.append(Claim(text=text, eids=eids))
    return claims


def numbers_grounded(claim_text: str, evidence_text: str) -> bool:
    """论断里出现的每个数字都必须在证据里出现（数值类反幻觉的硬规则）。"""
    nums = _NUMBER.findall(claim_text)
    if not nums:
        return True
    ev_nums = set(_NUMBER.findall(evidence_text))
    return all(n in ev_nums for n in nums)


class CitationVerifier:
    def __init__(
        self,
        nli: NLIModel,
        llm: LLMClient | None = None,
        *,
        threshold: float = 0.5,
    ) -> None:
        self._nli = nli
        self._llm = llm
        self._threshold = threshold

    async def _score_claim(self, claim: Claim, evidence: dict[str, Evidence]) -> tuple[float, str | None]:
        """返回 (最高蕴含概率, 最佳证据 id)。只在该句声明的 eid 范围内判定。"""
        cited = [e for e in claim.eids if e in evidence]
        if not cited:
            return 0.0, None
        pairs = [(evidence[eid].text, claim.text) for eid in cited]
        probs = await self._nli.entailment(pairs)
        best_i = max(range(len(probs)), key=probs.__getitem__)
        return probs[best_i], cited[best_i]

    async def verify(self, answer: str, evidence: dict[str, Evidence]) -> VerifiedAnswer:
        claims = split_claims(answer)
        for claim in claims:
            prob, best = await self._score_claim(claim, evidence)
            claim.best_eid = best
            grounded = best is not None and numbers_grounded(claim.text, evidence[best].text)
            claim.supported = prob >= self._threshold and grounded

            # 修复：不达标且有 LLM 时，依据证据重写一次
            if not claim.supported and self._llm is not None and best is not None:
                rewritten = await self._llm.complete(
                    _REWRITE_PROMPT.format(claim=claim.text, evidence=evidence[best].text)
                )
                cleaned = _clean_rewrite(rewritten)
                if cleaned:
                    claim.text = cleaned
                    prob2, _ = await self._score_claim(claim, evidence)
                    claim.supported = prob2 >= self._threshold and numbers_grounded(
                        claim.text, evidence[best].text
                    )

            if claim.best_eid is not None:
                claim.span = evidence[claim.best_eid].provenance

        # 可信度只在"带引用的论断"上计算：无引用的标题/过渡句不计入分母
        cited = [c for c in claims if c.eids]
        trust = (sum(c.supported for c in cited) / len(cited)) if cited else 0.0
        return VerifiedAnswer(answer=answer, claims=claims, trust=trust)


_REWRITE_PROMPT = (
    "下面这句话与引用的证据不完全吻合。请严格依据证据改写这句话，"
    "只保留证据支持的内容，不要新增证据之外的信息。\n\n"
    "证据：{evidence}\n\n原句：{claim}\n\n改写后："
)


def _clean_rewrite(text: str) -> str:
    """去掉 LLM 重写时可能带上的标签/代码块（如 "改写后：" "**...**"）。"""
    t = text.strip()
    for label in ("改写后：", "改写后:", "Rewritten:", "改写："):
        if t.startswith(label):
            t = t[len(label):].strip()
    t = t.strip("*").strip()
    return t
