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


@router.get("/api/exports/backup")
def backup(u=Depends(instructor)):
    tmp = tempfile.mkdtemp()
    dest = Path(tmp) / "backup.zip"
    try:
        db = database.get_connection()
        target = Path(tmp) / "iqterra.sqlite3"
        out = __import__("sqlite3").connect(target)
        db.backup(out)
        out.close()
        db.close()
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(target, "iqterra.sqlite3")
            uploads = database.DATA_DIR / "uploads"
            if uploads.is_dir():
                base = uploads.resolve()
                for f in uploads.iterdir():
                    if f.is_file() and f.resolve().parent == base:
                        z.write(f, "uploads/" + f.name)
        return FileResponse(
            dest,
            filename="iqterra-backup.zip",
            media_type="application/zip",
            background=__import__(
                "starlette.background", fromlist=["BackgroundTask"]
            ).BackgroundTask(lambda: shutil.rmtree(tmp, ignore_errors=True)),
        )
    except:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
