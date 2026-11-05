import os, secrets, tempfile, zipfile, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
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
from app.schemas import (
    Login,
    StudentIn,
    AssignmentIn,
    AllocationIn,
    ReviewDraft,
    ModerationIn,
    FlagIn,
)

router = APIRouter()
ph = PasswordHash.recommended()
PROMPTS = [
    "The submission demonstrates a clear understanding of the topic.",
    "Claims are supported by relevant evidence.",
    "The reasoning is coherent and well developed.",
    "The structure and writing are clear.",
    "The work offers thoughtful or original insight.",
]


@router.get("/api/students")
def students_list(u=Depends(instructor)):
    with database.get_connection() as c:
        return {
            "items": [
                dict(r)
                for r in c.execute(
                    "SELECT s.*,u.username,u.is_active FROM students s LEFT JOIN users u ON u.student_id=s.id ORDER BY s.display_name"
                )
            ],
            "students": [
                dict(r)
                for r in c.execute(
                    "SELECT s.*,u.username FROM students s LEFT JOIN users u ON u.student_id=s.id ORDER BY s.display_name"
                )
            ],
        }


@router.post("/api/students", status_code=201)
def create_student(x: StudentIn, u=Depends(instructor)):
    sid = secrets.token_hex(12)
    credential = secrets.token_urlsafe(24)
    try:
        with database.transaction(immediate=True) as c:
            c.execute(
                "INSERT INTO students(id,display_name) VALUES(?,?)",
                (sid, x.display_name),
            )
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id,must_change_password) VALUES(?,?,'student',?,1)",
                (x.username, ph.hash(credential), sid),
            )
    except Exception:
        raise HTTPException(409, "Student or username already exists")
    return {
        "id": sid,
        "username": x.username,
        "display_name": x.display_name,
        "one_time_credential": credential,
        "must_change_password": True,
    }
