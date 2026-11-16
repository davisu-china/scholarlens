"""全局配置。从环境变量 / .env 读取。"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SL_", extra="ignore")

    # --- storage ---
    postgres_dsn: str = "postgresql+psycopg://scholarlens:scholarlens@localhost:5432/scholarlens"
    qdrant_url: str = "http://localhost:6333"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "scholarlens"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    redis_url: str = "redis://localhost:6379/0"

    # --- LLM（经 LiteLLM；airouter 等 OpenAI 兼容网关填 base+key，官方 SDK 留空走环境变量）---
    strong_model: str = "claude-opus-5-5"          # Planner / Writer / 引用校验判官
    small_model: str = "claude-haiku-5-5"          # Reflector / query 改写 / 上下文前缀
    llm_api_base: str | None = None                # 如 https://airouter.cloud/v1
    llm_api_key: str | None = None
    # DeepSeek 官方直连（商业化时供用户选择的低价模型）
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_api_key: str | None = None

    # --- 向量化 / 重排（硅基流动 API，无需 GPU；key 写在 .env）---
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    siliconflow_api_base: str = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str | None = None

    # --- 引用校验：llm（用 LLM 判官，无需 GPU）| deberta（本地模型）---
    nli_mode: str = "llm"
    nli_model: str = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"

    # --- PDF 解析（MinerU 云 API；token 写在 .env，不进仓库）---
    mineru_api_token: str | None = None
    mineru_api_base: str = "https://mineru.net"
    mineru_model_version: str = "vlm"

    # --- auth ---
    jwt_secret: str = "change-me-in-production"
    billing_webhook_secret: str = "change-me-webhook-secret"
    jwt_algorithm: str = "HS256"

    # --- observability ---
    langfuse_host: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None


settings = Settings()
