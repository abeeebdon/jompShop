"""File upload / download routes using Emergent object storage."""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Header
from fastapi.responses import Response

from db import db
from auth import get_current_user, _user_from_jwt, _user_from_session_token
from models import User
from storage import put_object, get_object, guess_content_type, APP_NAME


router = APIRouter(prefix="/api", tags=["files"])


@router.post("/upload")
async def upload(file: UploadFile = File(...), kind: str = "general", user: User = Depends(get_current_user)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    path = f"{APP_NAME}/{kind}/{user.user_id}/{uuid.uuid4().hex}.{ext}"
    data = await file.read()
    ct = file.content_type or guess_content_type(file.filename)
    result = put_object(path, data, ct)
    doc = {
        "id": str(uuid.uuid4()),
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": ct,
        "size": result.get("size", len(data)),
        "kind": kind,
        "uploaded_by": user.user_id,
        "is_deleted": False,
    }
    await db.files.insert_one(doc)
    doc.pop("_id", None)
    return {"id": doc["id"], "storage_path": result["path"], "url": f"/api/files/{result['path']}", "size": doc["size"], "content_type": ct}


@router.get("/files/{path:path}")
async def download(path: str, request_auth: str | None = Query(None, alias="auth"), authorization: str | None = Header(None)):
    # accept token via Authorization: Bearer OR ?auth= (for <img src>)
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif request_auth:
        token = request_auth
    if not token:
        raise HTTPException(401, "auth token required")
    user = await _user_from_jwt(token) or await _user_from_session_token(token)
    if not user:
        raise HTTPException(401, "invalid token")

    rec = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404)
    data, ct = get_object(path)
    return Response(content=data, media_type=rec.get("content_type", ct))
