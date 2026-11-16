"""POST /auth/register, /auth/login — 真实登录，签发 JWT。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_users
from core.auth.jwt import create_token
from core.auth.users import BadCredentials, DuplicateUser, UserStore

router = APIRouter()


class Credentials(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/register", response_model=TokenResponse)
async def register(body: Credentials, users: UserStore = Depends(get_users)) -> TokenResponse:
    try:
        uid = await users.register(body.username, body.password)
    except DuplicateUser as e:
        raise HTTPException(409, str(e)) from e
    return TokenResponse(access_token=create_token(uid), user_id=uid)


@router.post("/login", response_model=TokenResponse)
async def login(body: Credentials, users: UserStore = Depends(get_users)) -> TokenResponse:
    try:
        uid = await users.authenticate(body.username, body.password)
    except BadCredentials as e:
        raise HTTPException(401, str(e)) from e
    return TokenResponse(access_token=create_token(uid), user_id=uid)
