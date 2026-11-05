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


@router.get("/api/overview")
def overview(assignment_id: int, u=Depends(instructor)):
    with database.get_connection() as c:
        a = c.execute(
            "SELECT * FROM assignments WHERE id=?", (assignment_id,)
        ).fetchone()
        if not a:
            raise HTTPException(404, "Assignment not found")
        students_data = []
        for s in c.execute(
            "SELECT id,display_name FROM students ORDER BY display_name"
        ):
            alloc = c.execute(
                "SELECT COUNT(*) FROM allocations WHERE assignment_id=? AND reviewer_id=?",
                (assignment_id, s["id"]),
            ).fetchone()[0]
            done = c.execute(
                "SELECT COUNT(*) FROM reviews r JOIN allocations x ON x.id=r.allocation_id WHERE x.assignment_id=? AND x.reviewer_id=? AND r.status='submitted'",
                (assignment_id, s["id"]),
            ).fetchone()[0]
            students_data.append(
                {
                    "id": s["id"],
                    "display_name": s["display_name"],
                    "allocated": alloc,
                    "submitted": done,
                    "status": "Complete" if alloc and done == alloc else "In progress",
                }
            )
        total = c.execute(
            "SELECT COUNT(*) FROM allocations WHERE assignment_id=?", (assignment_id,)
        ).fetchone()[0]
        complete = c.execute(
            "SELECT COUNT(*) FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE a.assignment_id=? AND r.status='submitted'",
            (assignment_id,),
        ).fetchone()[0]
        outcomes = []
        for q in c.execute(
            "SELECT * FROM questions WHERE assignment_id=? ORDER BY question_order",
            (assignment_id,),
        ):
            dist = {str(i): 0 for i in range(1, 6)}
            vals = [
                r[0]
                for r in c.execute(
                    "SELECT ra.score FROM review_answers ra JOIN reviews r ON r.id=ra.review_id JOIN allocations a ON a.id=r.allocation_id WHERE a.assignment_id=? AND ra.question_id=? AND r.status='submitted'",
                    (assignment_id, q["id"]),
                )
            ]
            for v in vals:
                dist[str(v)] += 1
            outcomes.append(
                {
                    "question_id": q["id"],
                    "prompt": q["prompt"],
                    "responses": len(vals),
                    "average_score": sum(vals) / len(vals) if vals else None,
                    "distribution": dist,
                }
            )
        return {
            "assignment": assignment(c, a),
            "students": students_data,
            "total_students": c.execute("SELECT COUNT(*) FROM students").fetchone()[0],
            "total_reviews": total,
            "completed_reviews": complete,
            "pending_reviews": total - complete,
            "moderation_count": c.execute(
                "SELECT COUNT(*) FROM review_flags f JOIN reviews r ON r.id=f.review_id JOIN allocations a ON a.id=r.allocation_id WHERE a.assignment_id=? AND f.status='open'",
                (assignment_id,),
            ).fetchone()[0],
            "question_outcomes": outcomes,
        }
