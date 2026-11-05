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


def questions(c, aid):
    return [
        dict(id=r["id"], prompt=r["prompt"], order=r["question_order"])
        for r in c.execute(
            "SELECT * FROM questions WHERE assignment_id=? ORDER BY question_order",
            (aid,),
        )
    ]


def assignment(c, r):
    d = dict(r)
    d["questions"] = questions(c, r["id"])
    return d


@router.get("/api/question-templates")
def templates():
    return {"items": [{"id": i + 1, "prompt": p} for i, p in enumerate(PROMPTS)]}


@router.get("/api/assignments")
def get_assignments(u=Depends(current_user)):
    with database.get_connection() as c:
        return [
            assignment(c, r)
            for r in c.execute("SELECT * FROM assignments ORDER BY id DESC")
        ]


@router.post("/api/assignments", status_code=201)
def create_assignment(x: AssignmentIn, u=Depends(instructor)):
    qs = x.questions or [{"prompt": p, "order": i + 1} for i, p in enumerate(PROMPTS)]
    if len(qs) != 5:
        raise HTTPException(422, "Exactly five questions are required")
    with database.transaction(immediate=True) as c:
        aid = c.execute(
            "INSERT INTO assignments(title,instructions,due_at) VALUES(?,?,?)",
            (x.title, x.instructions, x.due_at),
        ).lastrowid
        c.executemany(
            "INSERT INTO questions(assignment_id,prompt,question_order) VALUES(?,?,?)",
            [(aid, q["prompt"], q.get("order", i + 1)) for i, q in enumerate(qs)],
        )
        return assignment(
            c, c.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone()
        )


@router.get("/api/assignments/{aid}")
def get_assignment(aid: int, u=Depends(current_user)):
    with database.get_connection() as c:
        r = c.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone()
        if not r:
            raise HTTPException(404, "Assignment not found")
        return assignment(c, r)


@router.put("/api/assignments/{aid}")
def update_assignment(aid: int, x: AssignmentIn, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        r = c.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone()
        if not r:
            raise HTTPException(404, "Assignment not found")
        if c.execute(
            "SELECT 1 FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE a.assignment_id=? AND (r.status='submitted' OR EXISTS(SELECT 1 FROM review_answers ra WHERE ra.review_id=r.id))",
            (aid,),
        ).fetchone():
            raise HTTPException(409, "Rubric is locked after review creation")
        qs = x.questions or [
            {"prompt": p, "order": i + 1} for i, p in enumerate(PROMPTS)
        ]
        if len(qs) != 5:
            raise HTTPException(422, "Exactly five questions are required")
        c.execute(
            "UPDATE assignments SET title=?,instructions=?,due_at=? WHERE id=?",
            (x.title, x.instructions, x.due_at, aid),
        )
        existing = c.execute(
            "SELECT id FROM questions WHERE assignment_id=? ORDER BY question_order",
            (aid,),
        ).fetchall()
        for i, q in enumerate(qs):
            if i < len(existing):
                c.execute(
                    "UPDATE questions SET prompt=?,question_order=? WHERE id=?",
                    (q["prompt"], q.get("order", i + 1), existing[i]["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO questions(assignment_id,prompt,question_order) VALUES(?,?,?)",
                    (aid, q["prompt"], q.get("order", i + 1)),
                )
        for old in existing[len(qs) :]:
            c.execute("DELETE FROM questions WHERE id=?", (old["id"],))
        return assignment(
            c, c.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone()
        )


@router.post("/api/assignments/{aid}/allocations")
def alloc(aid: int, x: AllocationIn = AllocationIn(), u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        if c.execute("SELECT 1 FROM assignments WHERE id=?", (aid,)).fetchone() is None:
            raise HTTPException(404, "Assignment not found")
        if c.execute(
            "SELECT 1 FROM allocations WHERE assignment_id=?", (aid,)
        ).fetchone():
            raise HTTPException(409, "Allocations already exist")
        subs = c.execute(
            "SELECT id,student_id FROM submissions WHERE assignment_id=? ORDER BY student_id",
            (aid,),
        ).fetchall()
        try:
            pairs = allocate_reviews(
                [r["student_id"] for r in subs], x.reviewers_per_submission
            )
        except ValueError as e:
            raise HTTPException(422, str(e))
        ids = {r["student_id"]: r["id"] for r in subs}
        c.executemany(
            "INSERT INTO allocations(assignment_id,reviewer_id,submission_id) VALUES(?,?,?)",
            [(aid, rv, ids[sid]) for rv, sid in pairs],
        )
        out = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM allocations WHERE assignment_id=?", (aid,)
            )
        ]
    return {"items": out, "allocations": out}


@router.get("/api/allocations")
def allocations(assignment_id: int, u=Depends(instructor)):
    with database.get_connection() as c:
        return {
            "items": [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM allocations WHERE assignment_id=?", (assignment_id,)
                )
            ]
        }


@router.post("/api/assignments/{aid}/submissions")
def submit_work(
    aid: int,
    title: str = Form(...),
    content: str = Form(""),
    file: UploadFile | None = File(None),
    u=Depends(student),
):
    with database.get_connection() as c:
        a = c.execute(
            "SELECT status,due_at FROM assignments WHERE id=?", (aid,)
        ).fetchone()
    if not a:
        raise HTTPException(404, "Assignment not found")
    if a["status"] != "open" or due_passed(a["due_at"]):
        raise HTTPException(409, "Assignment is closed or past due")
    if file:
        data = file.file.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "File too large")
        ext = Path(file.filename or "").suffix.lower()
        if ext not in {".pdf", ".txt", ".doc", ".docx", ".png", ".jpg", ".jpeg"}:
            raise HTTPException(415, "Unsupported file type")
    else:
        data = None
        ext = ""
    if not (content or "").strip() and not data:
        raise HTTPException(422, "Provide text or an attachment")
    old_file = None
    with database.transaction(immediate=True) as c:
        live_assignment = c.execute(
            "SELECT status,due_at FROM assignments WHERE id=?", (aid,)
        ).fetchone()
        if not live_assignment:
            raise HTTPException(404, "Assignment not found")
        if live_assignment["status"] != "open" or due_passed(live_assignment["due_at"]):
            raise HTTPException(409, "Assignment is closed or past due")
        old = c.execute(
            "SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",
            (aid, u["student_id"]),
        ).fetchone()
        if (
            old
            and c.execute(
                "SELECT 1 FROM allocations WHERE submission_id=?", (old["id"],)
            ).fetchone()
        ):
            raise HTTPException(409, "Submission locked after allocation")
        filename = None
        if old and old["file_name"]:
            old_file = old["file_name"]
        if data:
            filename = secrets.token_hex(20) + ext
            folder = database.DATA_DIR / "uploads"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / filename).write_bytes(data)
        if old:
            c.execute(
                "UPDATE submissions SET title=?,content=?,file_name=?,original_file_name=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title, content, filename, file.filename if file else None, old["id"]),
            )
            sid = old["id"]
        else:
            sid = c.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content,file_name,original_file_name) VALUES(?,?,?,?,?,?)",
                (
                    aid,
                    u["student_id"],
                    title,
                    content,
                    filename,
                    file.filename if file else None,
                ),
            ).lastrowid
    if old_file and old_file != filename:
        base = (database.DATA_DIR / "uploads").resolve()
        target = (base / Path(old_file).name).resolve()
        if target.parent == base and target.is_file():
            target.unlink()
    return {"id": sid, "assignment_id": aid, "title": title, "content": content}


@router.get("/api/submissions/{sid}/file")
def file(sid: int, u=Depends(current_user)):
    with database.get_connection() as c:
        r = c.execute(
            "SELECT s.*, EXISTS(SELECT 1 FROM allocations a WHERE a.submission_id=s.id AND a.reviewer_id=?) assigned FROM submissions s WHERE s.id=?",
            (u["student_id"], sid),
        ).fetchone()
        if not r:
            raise HTTPException(404, "Submission not found")
        if (
            u["role"] == "student"
            and u["student_id"] != r["student_id"]
            and not r["assigned"]
        ):
            raise HTTPException(403, "Not authorized")
        if not r["file_name"]:
            raise HTTPException(404, "No file")
        base = (database.DATA_DIR / "uploads").resolve()
        p = (base / Path(r["file_name"]).name).resolve()
        if p.parent != base or not p.is_file():
            raise HTTPException(404, "File missing")
        return FileResponse(p, filename="submission" + p.suffix.lower())
