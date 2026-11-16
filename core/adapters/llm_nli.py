"""用 LLM 当"判官"做引用校验（core.ports.NLIModel 的 LLM 实现）。

替代本地 DeBERTa-NLI：对每个 (证据, 论断) 对，让 LLM 判断"证据是否支持该论断"，
返回 0–1 的支持度。好处是无需 GPU、对学术长句和跨语言（中文问/英文证据）更鲁棒；
代价是每对一次 API 调用——用小模型（haiku）即可，必要时并发。

一次 batch 内所有对并发请求。返回值与 NLIModel 契约一致（蕴含概率列表）。
"""

from __future__ import annotations

import asyncio
import re

from core.ports import LLMClient

_SCORE = re.compile(r"(?:0(?:\.\d+)?|1(?:\.0+)?)")

_JUDGE_PROMPT = """判断下面的"证据"是否支持"论断"。只看证据本身能不能推出论断，不要用你的外部知识。
输出一个 0 到 1 的小数：1 表示证据完全支持，0 表示证据无关或矛盾，中间值表示部分支持。
只输出这个数字，不要任何其他文字。

证据：{premise}

论断：{hypothesis}

支持度（0-1）："""


class LLMJudgeNLI:
    def __init__(
        self,
        llm: LLMClient,
        *,
        model: str | None = None,
        max_concurrency: int = 8,
    ) -> None:
        self._llm = llm
        self._model = model
        self._sem = asyncio.Semaphore(max_concurrency)

    async def _judge(self, premise: str, hypothesis: str) -> float:
        async with self._sem:
            raw = await self._llm.complete(
                _JUDGE_PROMPT.format(premise=premise, hypothesis=hypothesis), model=self._model
            )
        m = _SCORE.search(raw or "")
        if not m:
            return 0.0
        return max(0.0, min(1.0, float(m.group(0))))

    async def entailment(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        return list(await asyncio.gather(*(self._judge(p, h) for p, h in pairs)))
