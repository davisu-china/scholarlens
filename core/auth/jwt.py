"""JWT 签发与校验。用 python-jose（已在依赖里）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from core.config import settings


class AuthError(Exception):
    pass


def create_token(user_id: str, *, expires_hours: int = 24, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(hours=expires_hours)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    """校验并返回 user_id（sub）。失败抛 AuthError。"""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise AuthError(f"无效或过期的 token：{e}") from e
    sub = claims.get("sub")
    if not sub:
        raise AuthError("token 缺少 sub")
    return sub
