"""Auth utilities: JWT + Emergent session + bcrypt password hashing."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from dotenv import load_dotenv
from pathlib import Path

from db import db
from models import User

load_dotenv(Path(__file__).parent / ".env")

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = os.environ.get("JWT_ALG", "HS256")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))


# ---- password ----

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---- JWT ----

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None


# ---- session resolution ----

async def _user_from_jwt(token: str) -> Optional[User]:
    payload = decode_jwt(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return User(**doc) if doc else None


async def _user_from_session_token(token: str) -> Optional[User]:
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        return None
    expires_at = sess.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        return None
    doc = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    return User(**doc) if doc else None


async def get_current_user(request: Request) -> User:
    """Resolve user from (1) session_token cookie, (2) Authorization header (JWT or session_token)."""
    # 1. cookie
    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        user = await _user_from_session_token(cookie_token)
        if user:
            return user

    # 2. Authorization header
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        # Try JWT first
        user = await _user_from_jwt(token)
        if user:
            return user
        # Fallback: treat as emergent session token
        user = await _user_from_session_token(token)
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_optional_user(request: Request) -> Optional[User]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_roles(*roles: str):
    async def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {roles}")
        return user
    return dep
