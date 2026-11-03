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


@router.post("/api/demo/allocation")
def demo():
    ids = [f"demo-{i:02d}" for i in range(1, 11)]
    pairs = allocate_reviews(ids, 3)
    loads = {x: 0 for x in ids}
    for r, s in pairs:
        loads[r] += 1
    return {
        "assignments": [{"reviewer_id": r, "submission_id": s} for r, s in pairs],
        "assignment_count": len(pairs),
        "review_load_min": min(loads.values()),
        "review_load_max": max(loads.values()),
        "no_self": True,
        "no_reciprocal": True,
    }


@router.get("/manus-routes.json")
def manifest():
    return FileResponse(
        Path(__file__).resolve().parents[2] / "public" / "manus-routes.json",
        media_type="application/json",
    )
