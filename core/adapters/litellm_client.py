"""真实 LLM adapter：经 LiteLLM 统一路由。

支持两种接法：
- OpenAI 兼容网关（airouter / vLLM 等）：设 llm_api_base + llm_api_key，模型名自动加
  `openai/` 前缀走通用通道；
- 各家官方 SDK：留空 base，模型名用 LiteLLM 原生写法（claude-* / qwen-* / deepseek-*），
  key 走对应环境变量。

实现 core.ports.LLMClient。litellm 延迟导入，未安装不影响其余代码。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from pydantic import BaseModel

from core.config import settings
from core.llm import usage
from core.obs import langfuse as obs


class LiteLLMClient:
    def __init__(
        self,
        *,
        default_model: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        fallbacks: list[str] | None = None,
    ) -> None:
        self._default = default_model or settings.strong_model
        self._api_base = api_base if api_base is not None else settings.llm_api_base
        self._api_key = api_key if api_key is not None else settings.llm_api_key
        self._fallbacks = fallbacks or []

    def _model(self, model: str | None) -> str:
        name = model or self._default
        # 自定义 OpenAI 兼容网关：加 openai/ 前缀走通用通道（除非调用方已指定 provider）
        if self._api_base and "/" not in name:
            return f"openai/{name}"
        return name

    def _extra(self) -> dict:
        extra: dict = {}
        if self._api_base:
            extra["api_base"] = self._api_base
        if self._api_key:
            extra["api_key"] = self._api_key
        return extra

    @staticmethod
    def _tokens(resp) -> tuple[int, int]:
        u = getattr(resp, "usage", None)
        if not u:
            return 0, 0
        return (int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0))

    def _meter(self, model: str | None, resp) -> None:
        """把本次调用的 token 用量记入当前请求的累加器（按底层模型名计价）。"""
        u = getattr(resp, "usage", None)
        if not u:
            return
        usage.record(
            model or self._default,
            int(getattr(u, "prompt_tokens", 0) or 0),
            int(getattr(u, "completion_tokens", 0) or 0),
        )

    def _messages(self, prompt: str, system: str | None) -> list[dict]:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    async def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        import litellm

        concrete = model or self._default
        with obs.generation(obs._context().feature or "complete", concrete, prompt) as sink:
            resp = await litellm.acompletion(
                model=self._model(model),
                messages=self._messages(prompt, system),
                fallbacks=self._fallbacks or None,
                **self._extra(),
            )
            self._meter(model, resp)
            content = resp.choices[0].message.content or ""
            pt, ct = self._tokens(resp)
            sink(content, pt, ct)
        return content

    async def stream(
        self, prompt: str, *, model: str | None = None, system: str | None = None
    ) -> AsyncIterator[str]:
        import litellm

        stream = await litellm.acompletion(
            model=self._model(model),
            messages=self._messages(prompt, system),
            stream=True,
            stream_options={"include_usage": True},
            **self._extra(),
        )
        async for chunk in stream:
            if getattr(chunk, "usage", None):
                self._meter(model, chunk)
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def structured[T: BaseModel](self, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        """用 JSON schema 约束输出，解析为 Pydantic 模型。"""
        import litellm

        instruction = (
            f"{prompt}\n\n只输出严格符合以下 JSON Schema 的 JSON，不要额外文字、不要代码块：\n"
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
        )
        concrete = model or self._default
        with obs.generation(f"{obs._context().feature or 'structured'}:json", concrete, instruction) as sink:
            resp = await litellm.acompletion(
                model=self._model(model),
                messages=[{"role": "user", "content": instruction}],
                response_format={"type": "json_object"},
                **self._extra(),
            )
            self._meter(model, resp)
            content = resp.choices[0].message.content or "{}"
            pt, ct = self._tokens(resp)
            sink(content, pt, ct)
        return schema.model_validate_json(_strip_fence(content))


def _strip_fence(text: str) -> str:
    """去掉可能的 ```json ... ``` 包裹，提高 JSON 解析鲁棒性。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1].rsplit("```", 1)[0]
    return t.strip()
