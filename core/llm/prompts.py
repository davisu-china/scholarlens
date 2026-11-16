"""版本化的 prompt 模板（PRD 第 10/11 章）。

集中管理便于版本控制与评测复现。每个模板标注用途与期望输出格式。
"""

from __future__ import annotations

# ---- 深度研究 Agent ----

PLAN_PROMPT = """你是学术研究助手。把下面的研究问题拆解成 2-5 个有逻辑顺序的子问题，
每个子问题应当可以通过检索论文独立取证。只输出子问题，不要回答。

研究问题：{question}"""

INFO_POINTS_PROMPT = """为了充分回答下面这个子问题，需要哪些关键信息点？
列出 2-4 个具体的信息点（例如「方法 X 的困惑度」「方法 X 的训练成本」）。

子问题：{subquestion}"""

WRITE_PROMPT = """你是严谨的学术综述写作者。根据下面的证据回答研究问题。

要求：
1. 每个论断后必须用 [eid] 标注来源，eid 只能取自给定证据的 id，不得编造。
2. 只写证据支持的内容，证据不足的地方明确说明「现有文献未覆盖」。
3. 分点或分段组织，必要时给出对比。

研究问题：{question}

证据：
{evidence}

综述："""

# ---- 快速问答（PRD F2）----

QA_SYSTEM_PROMPT = """你是学术问答助手。只依据提供的证据回答，每个论断后用 [eid] 标注来源。
证据不足以回答时，明确拒答，不要编造。"""

QA_PROMPT = """问题：{question}

证据：
{evidence}

回答（每句以 [eid] 标注来源）："""

# ---- Contextual Chunking（见 core/index/chunker.py，这里留模板出处索引）----

# ---- 表格抽取（PRD 第 08 章）----

TABLE_EXTRACT_PROMPT = """从下面的实验结果表格中抽取所有 (方法, 数据集, 指标, 数值) 四元组。
方法名归一化（去掉括号里的超参，例如 "YaRN (s=16)" → "YaRN"）。
只抽取表格中真实出现的数值。

表格标题：{caption}
所在章节：{section}
表格内容（HTML）：
{html}"""


def format_evidence(evidence: dict) -> str:
    """把 {eid: Evidence} 渲染成给 LLM 的证据块。"""
    lines = []
    for eid, ev in evidence.items():
        src = ev.provenance.paper_id if hasattr(ev, "provenance") else ""
        lines.append(f"[{eid}] ({src}) {ev.text}")
    return "\n".join(lines)
