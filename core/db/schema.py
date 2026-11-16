"""SQLAlchemy 表定义（可移植：Postgres 生产 / SQLite 测试）。

只用通用列类型与标准 SQL，避免 PG 专有特性，保证同一套查询两边都能跑。
"""

from __future__ import annotations

from sqlalchemy import (
    Column, DateTime, Float, Integer, LargeBinary, MetaData, String, Table, text,
)

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", String(32), primary_key=True),
    Column("username", String(128), unique=True, nullable=False),
    Column("salt", LargeBinary, nullable=False),
    Column("pw_hash", LargeBinary, nullable=False),
)

subscriptions = Table(
    "subscriptions", metadata,
    Column("user_id", String(64), primary_key=True),
    Column("plan_id", String(32), nullable=False),
)

usage_events = Table(
    "usage_events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String(64), nullable=False, index=True),
    Column("action", String(32), nullable=False, index=True),
    Column("units", Integer, nullable=False, default=1),
    Column("model_id", String(64), nullable=True),
    Column("cost_cny", Float, nullable=False, default=0.0),
    Column("at", DateTime(timezone=True), nullable=False, index=True),
)

orders = Table(
    "orders", metadata,
    Column("id", String(32), primary_key=True),
    Column("user_id", String(64), nullable=False, index=True),
    Column("plan_id", String(32), nullable=False),
    Column("amount_cny", Float, nullable=False),
    Column("status", String(16), nullable=False, default="pending"),
)
