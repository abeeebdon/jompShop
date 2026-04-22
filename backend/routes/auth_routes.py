"""Auth routes: JWT email/password + Emergent Google OAuth session."""
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Body
from pydantic import BaseModel, EmailStr

from db import db
from models import User, UserPublic, RegisterRequest, LoginRequest, TokenResponse
from auth import hash_password, verify_password, create_jwt, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("helix.auth_routes")

EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


def _public(u: User) -> UserPublic:
    return UserPublic(user_id=u.user_id, email=u.email, name=u.name, role=u.role, business_id=u.business_id, picture=u.picture)


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest):
    existing = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        name=payload.name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        auth_provider="jwt",
    )
    doc = user.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.users.insert_one(doc)
    token = create_jwt(user.user_id)
    return TokenResponse(access_token=token, user=_public(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    doc = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not doc or not doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = User(**doc)
    token = create_jwt(user.user_id)
    return TokenResponse(access_token=token, user=_public(user))


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return _public(user)


class EmergentSessionRequest(BaseModel):
    session_id: str


@router.post("/emergent/session")
async def emergent_session(payload: EmergentSessionRequest, response: Response):
    # Call Emergent to resolve session_id
    try:
        r = requests.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": payload.session_id}, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error("Emergent session exchange failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid session")
    email = (data.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Invalid session response")

    # Upsert user
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user = User(**existing)
        # update picture/name if changed
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": {"name": data.get("name", user.name), "picture": data.get("picture", user.picture)}},
        )
    else:
        user = User(
            email=email,
            name=data.get("name", email.split("@")[0]),
            role="buyer",  # default for OAuth new users; upgradeable
            picture=data.get("picture"),
            auth_provider="emergent",
        )
        doc = user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.users.insert_one(doc)

    # Persist session
    session_token = data.get("session_token") or uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user.user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600,
        path="/",
    )
    return {"user": _public(user).model_dump(), "session_token": session_token}


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    if token:
        await db.user_sessions.delete_many({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"status": "ok"}
