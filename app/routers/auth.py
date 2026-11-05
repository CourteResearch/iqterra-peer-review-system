import os, secrets, tempfile, zipfile, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
from app.security import current_user
from app.allocation import allocate_reviews
from app.security import (
    current_user,
    instructor,
    student,
    JWT_SECRET,
    JWT_ALGORITHM,
    user_payload,
    due_passed,
)
from app.schemas import Login, PasswordChange

router = APIRouter()
ph = PasswordHash.recommended()
PROMPTS = [
    "The submission demonstrates a clear understanding of the topic.",
    "Claims are supported by relevant evidence.",
    "The reasoning is coherent and well developed.",
    "The structure and writing are clear.",
    "The work offers thoughtful or original insight.",
]


@router.post("/api/auth/login")
def login(x: Login):
    with database.get_connection() as c:
        r = c.execute(
            "SELECT * FROM users WHERE username=? COLLATE NOCASE", (x.username,)
        ).fetchone()
    if not r or not r["is_active"] or not ph.verify(x.password, r["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = jwt.encode(
        {"sub": str(r["id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with database.get_connection() as c:
        row = c.execute(
            "SELECT u.*,s.display_name FROM users u LEFT JOIN students s ON s.id=u.student_id WHERE u.id=?",
            (r["id"],),
        ).fetchone()
    return {
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "user": user_payload(row),
    }


@router.get("/api/auth/me")
def me(u=Depends(current_user)):
    return user_payload(u)


@router.post("/api/auth/password")
def change_password(x: PasswordChange, u=Depends(current_user)):
    if len(x.new_password) < 12:
        raise HTTPException(422, "New password must be at least 12 characters")
    if not ph.verify(x.current_password, u["password_hash"]):
        raise HTTPException(403, "Current password is incorrect")
    with database.transaction(immediate=True) as c:
        c.execute(
            "UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
            (ph.hash(x.new_password), u["id"]),
        )
        row = c.execute(
            "SELECT u.*,s.display_name FROM users u LEFT JOIN students s ON s.id=u.student_id WHERE u.id=?",
            (u["id"],),
        ).fetchone()
    return {"ok": True, "user": user_payload(row)}
