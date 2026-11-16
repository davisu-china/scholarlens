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

    # --- models (via LiteLLM) ---
    strong_model: str = "claude-sonnet-4-5"       # Planner / Writer
    small_model: str = "qwen-plus"                # Reflector / query rewrite
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    nli_model: str = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"

    # --- auth ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # --- observability ---
    langfuse_host: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None


settings = Settings()
