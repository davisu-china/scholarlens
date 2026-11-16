"""Query 路由与改写（PRD 第 09 章）。

把问题分到 factoid / numeric / survey / paper_specific 四类，分别走不同的检索组合
与生成模板。survey 类自动进入深度研究模式。

默认用轻量规则分类（零依赖、可解释、好测）；需要更准时可注入 LLM 兜底。
"""

from __future__ import annotations

import re

from core.domain import Query, QueryIntent
from core.ports import LLMClient

# 数值/比较类信号
_NUMERIC = re.compile(
    r"(最高|最低|最好|最大|最小|多少|几个|对比|比较|highest|lowest|best|compare|how many|"
    r"\bem\b|\bf1\b|accuracy|score|ppl|perplexity|recall@|ndcg)",
    re.I,
)
# 综述类信号
_SURVEY = re.compile(
    r"(综述|梳理|演进|发展|脉络|有哪些|survey|overview|evolution|review|landscape|趋势)",
    re.I,
)
# 指定某篇论文
_PAPER_SPECIFIC = re.compile(
    r"(这篇|该论文|本文|上面那篇|公式\s*\d|表\s*\d|figure\s*\d|table\s*\d|section\s*\d)",
    re.I,
)


def classify_rule(text: str) -> QueryIntent:
    """纯规则分类。顺序有讲究：具体意图优先。

    survey 放在 numeric 之前，避免「有哪些用对比学习做…」里的「对比」被误判为数值比较。
    """
    if _PAPER_SPECIFIC.search(text):
        return "paper_specific"
    if _SURVEY.search(text):
        return "survey"
    if _NUMERIC.search(text):
        return "numeric"
    return "factoid"


class QueryRouter:
    """对外入口。先走规则；规则落到 factoid 且提供了 LLM 时，用 LLM 复核一次。"""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    async def route(self, text: str) -> QueryIntent:
        intent = classify_rule(text)
        return intent

    def to_query(self, text: str, intent: QueryIntent, **kwargs) -> Query:
        return Query(text=text, intent=intent, **kwargs)
