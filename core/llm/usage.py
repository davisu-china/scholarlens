"""按请求收集 LLM token 用量（contextvar，请求级隔离）。

LLM adapter 每次调用后把 (model, input, output) 推进来；API 处理完一个请求后
collect() 得到总 token 与总成本，写入计费。
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field

from core.llm.pricing import cost_cny


@dataclass
class _Entry:
    model: str
    input_tokens: int
    output_tokens: int


@dataclass
class UsageAccumulator:
    entries: list[_Entry] = field(default_factory=list)

    def push(self, model: str, input_tokens: int, output_tokens: int) -> None:
        self.entries.append(_Entry(model, input_tokens, output_tokens))

    @property
    def total_tokens(self) -> int:
        return sum(e.input_tokens + e.output_tokens for e in self.entries)

    @property
    def total_cost_cny(self) -> float:
        return round(sum(cost_cny(e.model, e.input_tokens, e.output_tokens) for e in self.entries), 6)


_current: contextvars.ContextVar[UsageAccumulator | None] = contextvars.ContextVar(
    "llm_usage", default=None
)


def start() -> UsageAccumulator:
    """开启一个新的请求级累加器并设为当前。"""
    acc = UsageAccumulator()
    _current.set(acc)
    return acc


def record(model: str, input_tokens: int, output_tokens: int) -> None:
    acc = _current.get()
    if acc is not None:
        acc.push(model, input_tokens, output_tokens)
