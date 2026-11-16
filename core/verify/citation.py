"""引用校验与反幻觉：生成后用 NLI 逐句验证每条引用是否成立。

这是本项目最核心的差异点。参见 PRD 第 11 章。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.retrieval.hybrid import Evidence
from core.ingest.schema import BBox


@dataclass
class Claim:
    text: str                      # 单条论断
    eids: list[str]                # 它引用的证据 id
    supported: bool = False
    span: BBox | None = None       # 命中证据内最相似句子的 bbox，用于精确高亮
    best_eid: str | None = None


@dataclass
class VerifiedAnswer:
    claims: list[Claim] = field(default_factory=list)
    trust: float = 0.0             # 可信度 = 有据论断占比


def split_claims(answer: str) -> list[Claim]:
    """把答案切成 (论断, [eid...]) 对；引用多源的句子拆成多条。"""
    raise NotImplementedError("TODO: 句子切分 + 从句尾 [eid] 提取引用")


def numbers_grounded(claim: Claim, evidence: dict[str, Evidence]) -> bool:
    """数值类论断额外做规则校验：数字必须在原文中出现。"""
    raise NotImplementedError("TODO: 数值规则校验")


def locate_span(claim_text: str, evidence: Evidence) -> BBox | None:
    """在证据 chunk 内找与论断最相似的句子，返回其 bbox。"""
    raise NotImplementedError("TODO: 句级 span 定位")


def verify_claims(answer: str, evidence: dict[str, Evidence]) -> VerifiedAnswer:
    """NLI 阈值 0.5（上线前在 200 条人工标注对上按 Precision 优先重新标定）。"""
    raise NotImplementedError(
        "TODO: DeBERTa-NLI 批量计算 P(证据蕴含论断)，<0.5 的句子交 LLM 重写一次"
    )
