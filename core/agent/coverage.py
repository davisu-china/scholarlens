"""证据覆盖度计算（PRD 第 10 章）。

深度研究 Agent 用覆盖度（而非固定轮数）决定是否继续补检索：
  覆盖度 = 已覆盖信息点数 / 总信息点数
未覆盖的信息点直接转成下一轮的补充查询，使补检索有明确目标。

这里是纯逻辑，便于单测；信息点的「是否被覆盖」判定通过注入的匹配函数完成
（真实实现可用 NLI / embedding 相似度，测试用词重叠）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CoverageReport:
    coverage: float
    covered: list[str]
    missing: list[str]

    @property
    def is_sufficient(self) -> bool:
        return self.coverage >= 0.8


def compute_coverage(
    info_points: list[str],
    evidence_texts: list[str],
    is_covered: Callable[[str, list[str]], bool],
) -> CoverageReport:
    """给定一组「需要回答的信息点」和已有证据，算出覆盖度。

    Args:
        info_points: Reflector 列出的信息点，如 ["PI 的困惑度", "PI 的训练成本"]。
        evidence_texts: 当前已检索到的证据文本。
        is_covered: 判定某信息点是否被证据覆盖的谓词（可注入不同策略）。
    """
    if not info_points:
        return CoverageReport(coverage=1.0, covered=[], missing=[])
    covered, missing = [], []
    for point in info_points:
        (covered if is_covered(point, evidence_texts) else missing).append(point)
    return CoverageReport(
        coverage=len(covered) / len(info_points), covered=covered, missing=missing
    )


def token_overlap_covered(point: str, evidence_texts: list[str], *, ratio: float = 0.5) -> bool:
    """默认判定：信息点的词被任一证据覆盖超过 ratio 即算覆盖。"""
    import re

    def toks(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9一-鿿]+", s.lower()))

    p = toks(point)
    if not p:
        return True
    return any(len(p & toks(ev)) / len(p) >= ratio for ev in evidence_texts)
