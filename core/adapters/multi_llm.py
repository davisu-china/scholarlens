"""多网关 LLM：按模型 id 路由到各自的端点与 key（core.ports.LLMClient 实现）。

商业化多模型选择的落地：Claude 走 airouter、DeepSeek 走官方端点，各用各的 base/key。
调用时 `model` 传模型目录里的友好 id（如 "opus" / "deepseek"），内部解析到对应的
LiteLLMClient。未指定时用默认模型。

对业务层透明：QAService / ResearchCoordinator 仍只依赖 LLMClient 接口，按请求把用户
选择的模型 id 透传下来即可。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import BaseModel

from core.adapters.litellm_client import LiteLLMClient
from core.llm.catalog import ModelSpec, build_catalog, default_strong_id


class MultiGatewayLLM:
    def __init__(
        self,
        catalog: dict[str, ModelSpec] | None = None,
        *,
        default_id: str | None = None,
    ) -> None:
        self._catalog = catalog if catalog is not None else build_catalog()
        if not self._catalog:
            raise RuntimeError("模型目录为空：至少配置一个网关的 key（见 .env）")
        self._default_id = default_id or default_strong_id(self._catalog)
        self._clients: dict[str, LiteLLMClient] = {
            mid: LiteLLMClient(default_model=spec.model, api_base=spec.api_base, api_key=spec.api_key)
            for mid, spec in self._catalog.items()
        }

    def _resolve(self, model: str | None) -> LiteLLMClient:
        mid = model or self._default_id
        client = self._clients.get(mid)
        if client is None:
            raise ValueError(f"未知或不可用的模型 id：{mid}（可用：{sorted(self._clients)}）")
        return client

    async def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        return await self._resolve(model).complete(prompt, system=system)

    def stream(
        self, prompt: str, *, model: str | None = None, system: str | None = None
    ) -> AsyncIterator[str]:
        return self._resolve(model).stream(prompt, system=system)

    async def structured[T: BaseModel](self, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        return await self._resolve(model).structured(prompt, schema)
