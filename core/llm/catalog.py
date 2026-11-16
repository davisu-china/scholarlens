"""模型目录：用户可选的 LLM 清单（商业化多模型选择）。

每个模型是一个 ModelSpec，记录它经哪个网关、用哪个 key、具体模型名、以及给用户看的
标签/说明/档位。目录由 settings 构建——只有配置了对应 key 的网关才会出现在清单里。

设计：以"友好 id"作为对外选择标识（如 "opus"/"deepseek"），与具体底层模型名解耦，
这样将来换底层模型不影响用户已保存的选择。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config import settings

Tier = str  # "flagship" | "balanced" | "cheap"


@dataclass(frozen=True)
class ModelSpec:
    id: str              # 对外选择标识，如 "opus" / "deepseek"
    label: str           # 界面显示名
    description: str     # 给用户的一句话说明
    tier: Tier
    model: str           # 底层模型名（传给网关）
    api_base: str | None
    api_key: str | None

    @property
    def available(self) -> bool:
        return bool(self.api_key)


def build_catalog() -> dict[str, ModelSpec]:
    """按配置构建可用模型目录。未配置 key 的模型不纳入。"""
    specs = [
        ModelSpec(
            id="opus",
            label="Claude Opus 5.5",
            description="最强，适合复杂综述与多跳推理；较贵。",
            tier="flagship",
            model="claude-opus-5-5",
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
        ),
        ModelSpec(
            id="haiku",
            label="Claude Haiku 5.5",
            description="快而省，适合问答与反思改写。",
            tier="cheap",
            model="claude-haiku-5-5",
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
        ),
        ModelSpec(
            id="deepseek",
            label="DeepSeek Chat",
            description="最便宜，能力稍弱，适合预算敏感或大批量场景。",
            tier="cheap",
            model="deepseek-chat",
            api_base=settings.deepseek_api_base,
            api_key=settings.deepseek_api_key,
        ),
        ModelSpec(
            id="deepseek-pro",
            label="DeepSeek V4 Pro",
            description="DeepSeek 旗舰，性价比高。",
            tier="balanced",
            model="deepseek-v4-pro",
            api_base=settings.deepseek_api_base,
            api_key=settings.deepseek_api_key,
        ),
    ]
    return {s.id: s for s in specs if s.available}


def default_strong_id(catalog: dict[str, ModelSpec]) -> str:
    """默认强模型：优先 opus，否则任意 flagship/balanced，再否则任意。"""
    for pref in ("opus", "deepseek-pro", "deepseek", "haiku"):
        if pref in catalog:
            return pref
    return next(iter(catalog))


def default_cheap_id(catalog: dict[str, ModelSpec]) -> str:
    """默认小模型：优先 haiku，否则 deepseek，再否则任意。"""
    for pref in ("haiku", "deepseek", "deepseek-pro", "opus"):
        if pref in catalog:
            return pref
    return next(iter(catalog))
