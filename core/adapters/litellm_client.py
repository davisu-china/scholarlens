"""真实 LLM adapter：经 LiteLLM 统一路由到 Claude / Qwen / DeepSeek / vLLM。

实现 core.ports.LLMClient。重依赖 litellm 延迟导入，未安装时不影响其余代码。
⚠️ 需真实 API key 与网络，无法在无依赖的沙箱里联调。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from pydantic import BaseModel

from core.config import settings


class LiteLLMClient:
    def __init__(self, *, default_model: str | None = None, fallbacks: list[str] | None = None) -> None:
        self._default = default_model or settings.strong_model
        self._fallbacks = fallbacks or []

    def _messages(self, prompt: str, system: str | None) -> list[dict]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    async def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        import litellm

        resp = await litellm.acompletion(
            model=model or self._default,
            messages=self._messages(prompt, system),
            fallbacks=self._fallbacks or None,
        )
        return resp.choices[0].message.content or ""

    async def stream(
        self, prompt: str, *, model: str | None = None, system: str | None = None
    ) -> AsyncIterator[str]:
        import litellm

        stream = await litellm.acompletion(
            model=model or self._default,
            messages=self._messages(prompt, system),
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def structured[T: BaseModel](self, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        """用 JSON schema 约束输出（response_format），解析为 Pydantic 模型。"""
        import litellm

        instruction = (
            f"{prompt}\n\n只输出严格符合以下 JSON Schema 的 JSON，不要额外文字：\n"
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
        )
        resp = await litellm.acompletion(
            model=model or self._default,
            messages=[{"role": "user", "content": instruction}],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return schema.model_validate_json(content)
