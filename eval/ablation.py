"""消融实验矩阵（PRD 第 12 章）。

每一行在上一行基础上加一个组件，用来量化每个优化的收益。文档只给实验矩阵，
数值由 run_ablation 实测填入（CI 跑冒烟集，核心指标下降超 2 点就阻止合并）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from core.qa import QAService
from eval.dataset import EvalExample
from eval.runner import EvalReport, run_suite


@dataclass(frozen=True)
class AblationConfig:
    """一个消融配置。布尔开关对应检索/生成链路里的各组件。"""

    name: str
    layout_parse: bool = False      # MinerU 版面解析（否则 PyPDF + 固定切分）
    contextual_chunk: bool = False  # Contextual Chunking
    hybrid: bool = False            # Dense+Sparse + RRF（否则仅 Dense）
    rerank: bool = False            # Cross-Encoder 重排（微调版）
    verify: bool = False            # NLI 引用校验 + 重写
    agent: bool = False             # 深度研究 Agent（仅多跳/综述题）


# B0 → +6，与 PRD 表格一一对应
ABLATION_MATRIX: list[AblationConfig] = [
    AblationConfig("B0 Baseline"),
    AblationConfig("+1 Layout+Section", layout_parse=True),
    AblationConfig("+2 Contextual", layout_parse=True, contextual_chunk=True),
    AblationConfig("+3 Hybrid+RRF", layout_parse=True, contextual_chunk=True, hybrid=True),
    AblationConfig("+4 Rerank", layout_parse=True, contextual_chunk=True, hybrid=True, rerank=True),
    AblationConfig("+5 Verify", layout_parse=True, contextual_chunk=True, hybrid=True, rerank=True, verify=True),
    AblationConfig("+6 Agent", layout_parse=True, contextual_chunk=True, hybrid=True, rerank=True, verify=True, agent=True),
]


@dataclass
class AblationRow:
    config: AblationConfig
    report: EvalReport


async def run_ablation(
    build_qa: Callable[[AblationConfig], Awaitable[QAService]],
    examples: list[EvalExample],
    *,
    matrix: list[AblationConfig] | None = None,
) -> list[AblationRow]:
    """对每个配置构建对应的 QA 服务并评测。build_qa 由调用方按开关装配不同 adapter。"""
    rows: list[AblationRow] = []
    for cfg in matrix or ABLATION_MATRIX:
        qa = await build_qa(cfg)
        report = await run_suite(qa, examples, suite=cfg.name)
        rows.append(AblationRow(config=cfg, report=report))
    return rows
