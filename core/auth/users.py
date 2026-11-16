"""用户存储（雏形内存版；生产换 Postgres，接口不变）。

密码用 PBKDF2-HMAC-SHA256 加盐哈希，不存明文。
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


@dataclass
class User:
    id: str
    username: str
    salt: bytes
    pw_hash: bytes


class DuplicateUser(Exception):
    pass


class BadCredentials(Exception):
    pass


@runtime_checkable
class UserStore(Protocol):
    async def register(self, username: str, password: str) -> str: ...
    async def authenticate(self, username: str, password: str) -> str: ...


class InMemoryUserStore:
    def __init__(self) -> None:
        self._by_name: dict[str, User] = {}

    async def register(self, username: str, password: str) -> str:
        if username in self._by_name:
            raise DuplicateUser(f"用户名已存在：{username}")
        salt = os.urandom(16)
        uid = uuid.uuid4().hex[:12]
        self._by_name[username] = User(id=uid, username=username, salt=salt, pw_hash=_hash(password, salt))
        return uid

    async def authenticate(self, username: str, password: str) -> str:
        user = self._by_name.get(username)
        if user is None or not hmac.compare_digest(user.pw_hash, _hash(password, user.salt)):
            raise BadCredentials("用户名或密码错误")
        return user.id
