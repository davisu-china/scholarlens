"""模型价格表（人民币/千 token）。

用于把 token 用量换算成成本。数值为估算，按各家公开价折算，**务必按实际账单校准**。
键为底层模型名（与 catalog.ModelSpec.model 一致）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    input_per_1k: float   # 输入 token 单价（元/千）
    output_per_1k: float  # 输出 token 单价（元/千）


# 估算值，上线前以真实账单校准
PRICES: dict[str, Price] = {
    "claude-opus-5-5": Price(input_per_1k=0.11, output_per_1k=0.55),
    "claude-haiku-5-5": Price(input_per_1k=0.007, output_per_1k=0.035),
    "deepseek-chat": Price(input_per_1k=0.001, output_per_1k=0.002),
    "deepseek-v4-pro": Price(input_per_1k=0.004, output_per_1k=0.012),
}

_DEFAULT = Price(input_per_1k=0.01, output_per_1k=0.03)


def cost_cny(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICES.get(model, _DEFAULT)
    return round(input_tokens / 1000 * p.input_per_1k + output_tokens / 1000 * p.output_per_1k, 6)
