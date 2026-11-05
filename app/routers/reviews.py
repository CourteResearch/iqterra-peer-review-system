import os, secrets, tempfile, zipfile, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
from app.helpers import questions
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


def review_access(c, rid, u, create=False):
    if u["role"] == "student":
        allocation = c.execute(
            "SELECT * FROM allocations WHERE id=?", (rid,)
        ).fetchone()
        if not allocation:
            raise HTTPException(404, "Review allocation not found")
        if allocation["reviewer_id"] != u["student_id"]:
            raise HTTPException(403, "Not assigned to this review")
        r = c.execute(
            "SELECT r.*,a.reviewer_id,a.submission_id,a.assignment_id FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE a.id=?",
            (rid,),
        ).fetchone()
        if not r and create:
            c.execute("INSERT INTO reviews(allocation_id) VALUES(?)", (rid,))
            r = c.execute(
                "SELECT r.*,a.reviewer_id,a.submission_id,a.assignment_id FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE a.id=?",
                (rid,),
            ).fetchone()
        if not r:
            return {
                "id": None,
                "status": "draft",
                "feedback": "",
                "reviewer_id": allocation["reviewer_id"],
                "submission_id": allocation["submission_id"],
                "assignment_id": allocation["assignment_id"],
                "allocation_id": rid,
            }
        return r

    r = c.execute(
        "SELECT r.*,a.reviewer_id,a.submission_id,a.assignment_id FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE r.id=?",
        (rid,),
    ).fetchone()
    allocation = (
        c.execute("SELECT * FROM allocations WHERE id=?", (rid,)).fetchone()
        if not r
        else None
    )
    if allocation:
        if u["role"] == "student" and u["student_id"] != allocation["reviewer_id"]:
            raise HTTPException(403, "Not assigned to this review")
        r = c.execute(
            "SELECT r.*,a.reviewer_id,a.submission_id,a.assignment_id FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE r.allocation_id=?",
            (rid,),
        ).fetchone()
        if not r and create:
            c.execute("INSERT INTO reviews(allocation_id) VALUES(?)", (rid,))
            r = c.execute(
                "SELECT r.*,a.reviewer_id,a.submission_id,a.assignment_id FROM reviews r JOIN allocations a ON a.id=r.allocation_id WHERE r.allocation_id=?",
                (rid,),
            ).fetchone()
        if not r:
            return {
                "id": None,
                "status": "draft",
                "feedback": "",
                "reviewer_id": allocation["reviewer_id"],
                "submission_id": allocation["submission_id"],
                "assignment_id": allocation["assignment_id"],
                "allocation_id": rid,
            }
    if not r:
        raise HTTPException(404, "Review not found")
    if u["role"] == "student" and u["student_id"] != r["reviewer_id"]:
        raise HTTPException(403, "Not assigned to this review")
    return r


@router.get("/api/my/reviews")
def my_reviews(u=Depends(student)):
    with database.get_connection() as c:
        rows = c.execute(
            "SELECT a.id allocation_id,a.assignment_id,ass.due_at,s.id submission_id,s.title,s.file_name,COALESCE(r.status,'draft') status,r.id review_id FROM allocations a JOIN assignments ass ON ass.id=a.assignment_id JOIN submissions s ON s.id=a.submission_id LEFT JOIN reviews r ON r.allocation_id=a.id WHERE a.reviewer_id=? ORDER BY a.id",
            (u["student_id"],),
        ).fetchall()
        items = []
        for row in rows:
            rid = row["allocation_id"]
            items.append(
                {
                    "id": rid,
                    "allocation_id": row["allocation_id"],
                    "assignment_id": row["assignment_id"],
                    "submission_id": row["submission_id"],
                    "title": row["title"],
                    "status": row["status"],
                    "due_at": row["due_at"],
                    "submission": {
                        "id": row["submission_id"],
                        "title": row["title"],
                        **(
                            {"file_url": f"/api/submissions/{row['submission_id']}/file"}
                            if row["file_name"]
                            else {}
                        ),
                    },
                }
            )
        return {"items": items}


@router.get("/api/reviews/{rid}")
def review_get(rid: int, u=Depends(current_user)):
    with database.get_connection() as c:
        r = review_access(c, rid, u)
        rid = r["id"] or rid
        sub = c.execute(
            "SELECT * FROM submissions WHERE id=?", (r["submission_id"],)
        ).fetchone()
        answers = [
            dict(question_id=z["question_id"], score=z["score"])
            for z in c.execute("SELECT * FROM review_answers WHERE review_id=?", (rid,))
        ]
        return {
            "id": r["allocation_id"] if u["role"] == "student" else rid,
            "status": r["status"],
            "feedback": r["feedback"],
            "answers": answers,
            "submission": {
                "title": sub["title"],
                "content": sub["content"],
                "questions": questions(c, r["assignment_id"]),
                **(
                    {"file_url": f"/api/submissions/{sub['id']}/file"}
                    if sub["file_name"]
                    else {}
                ),
            },
        }


@router.put("/api/reviews/{rid}")
def review_put(rid: int, x: ReviewDraft, u=Depends(student)):
    with database.transaction(immediate=True) as c:
        r = review_access(c, rid, u, create=True)
        rid = (
            r["id"]
            or c.execute(
                "SELECT id FROM reviews WHERE allocation_id=?", (r["allocation_id"],)
            ).fetchone()[0]
        )
        if r["status"] == "submitted":
            raise HTTPException(409, "Review already submitted")
        c.execute(
            "UPDATE reviews SET feedback=?,status='draft',updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (x.feedback, rid),
        )
        qids = [int(a["question_id"]) for a in x.answers]
        if len(qids) != len(set(qids)):
            raise HTTPException(422, "Duplicate question IDs")
        allowed = {
            z[0]
            for z in c.execute(
                "SELECT id FROM questions WHERE assignment_id=?", (r["assignment_id"],)
            )
        }
        for a in x.answers:
            if int(a["question_id"]) not in allowed:
                raise HTTPException(422, "Question does not belong to assigned rubric")
            if int(a["score"]) not in range(1, 6):
                raise HTTPException(422, "Scores must be 1–5")
            c.execute(
                "INSERT INTO review_answers(review_id,question_id,score) VALUES(?,?,?) ON CONFLICT(review_id,question_id) DO UPDATE SET score=excluded.score",
                (rid, a["question_id"], a["score"]),
            )
    return {"id": rid, "status": "draft"}


@router.post("/api/reviews/{rid}/submit")
def review_submit(rid: int, u=Depends(student)):
    with database.transaction(immediate=True) as c:
        r = review_access(c, rid, u, create=True)
        rid = (
            r["id"]
            or c.execute(
                "SELECT id FROM reviews WHERE allocation_id=?", (r["allocation_id"],)
            ).fetchone()[0]
        )
        if r["status"] == "submitted":
            raise HTTPException(409, "Already submitted")
        q = c.execute(
            "SELECT COUNT(*) FROM questions WHERE assignment_id=?",
            (r["assignment_id"],),
        ).fetchone()[0]
        n = c.execute(
            "SELECT COUNT(*) FROM review_answers ra JOIN questions q ON q.id=ra.question_id WHERE ra.review_id=? AND q.assignment_id=?",
            (rid, r["assignment_id"]),
        ).fetchone()[0]
        if q != 5 or n != 5 or len(r["feedback"].strip()) < 10:
            raise HTTPException(
                422, "All five scores and at least 10 feedback characters are required"
            )
        c.execute(
            "UPDATE reviews SET status='submitted',submitted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (rid,),
        )
    return {"id": rid, "status": "submitted"}


@router.post("/api/reviews/{rid}/flag", status_code=201)
def flag(rid: int, x: FlagIn, u=Depends(student)):
    with database.transaction(immediate=True) as c:
        r = review_access(c, rid, u, create=True)
        review_id = r["id"]
        if c.execute(
            "SELECT 1 FROM review_flags WHERE review_id=? AND status='open'",
            (review_id,),
        ).fetchone():
            raise HTTPException(409, "Open flag already exists")
        fid = c.execute(
            "INSERT INTO review_flags(review_id,reporter_student_id,reason) VALUES(?,?,?)",
            (review_id, u["student_id"], x.reason),
        ).lastrowid
    return {"id": fid, "status": "open"}


@router.get("/api/moderation")
def moderation(assignment_id: int | None = None, u=Depends(instructor)):
    with database.get_connection() as c:
        q = "SELECT f.id,f.review_id,f.reason,f.status,f.created_at,s.title submission_title,s.content submission_content,r.feedback,s.id submission_id,a.assignment_id FROM review_flags f JOIN reviews r ON r.id=f.review_id JOIN allocations a ON a.id=r.allocation_id JOIN submissions s ON s.id=a.submission_id WHERE f.status='open'"
        args = []
        if assignment_id is not None:
            q += " AND a.assignment_id=?"
            args.append(assignment_id)
        items = []
        for row in c.execute(q, args):
            item = dict(row)
            item["file_url"] = (
                f"/api/submissions/{item['submission_id']}/file"
                if c.execute(
                    "SELECT file_name FROM submissions WHERE id=?",
                    (item["submission_id"],),
                ).fetchone()[0]
                else None
            )
            item["questions"] = questions(c, item["assignment_id"])
            item["answers"] = [
                dict(question_id=a["question_id"], score=a["score"])
                for a in c.execute(
                    "SELECT question_id,score FROM review_answers WHERE review_id=?",
                    (item["review_id"],),
                )
            ]
            items.append(item)
        return {"items": items}


@router.post("/api/reviews/{rid}/moderation")
def moderate(rid: int, x: ModerationIn, u=Depends(instructor)):
    if x.decision not in ("approved", "dismissed"):
        raise HTTPException(422, "Invalid decision")
    with database.transaction(immediate=True) as c:
        if not c.execute("SELECT 1 FROM reviews WHERE id=?", (rid,)).fetchone():
            raise HTTPException(404, "Review not found")
        c.execute(
            "INSERT INTO moderation_events(review_id,moderator_id,decision,note) VALUES(?,?,?,?)",
            (rid, u["id"], x.decision, x.note),
        )
        c.execute(
            "UPDATE review_flags SET status=?,decision=?,moderator_id=?,moderation_note=?,resolved_at=CURRENT_TIMESTAMP WHERE review_id=? AND status='open'",
            (x.decision, x.decision, u["id"], x.note, rid),
        )
        c.execute(
            "INSERT INTO review_audit(review_id,actor_id,action,detail) VALUES(?,?,?,?)",
            (rid, u["id"], "moderation", x.decision + ": " + x.note),
        )
    return {"review_id": rid, "decision": x.decision}


@router.post("/api/reviews/{rid}/reopen")
def reopen(rid: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        r = c.execute("SELECT status FROM reviews WHERE id=?", (rid,)).fetchone()
        if not r:
            raise HTTPException(404, "Review not found")
        if r["status"] != "submitted":
            raise HTTPException(409, "Only submitted reviews may be reopened")
        c.execute(
            "UPDATE reviews SET status='reopened',submitted_at=NULL WHERE id=?", (rid,)
        )
        c.execute(
            "INSERT INTO review_audit(review_id,actor_id,action) VALUES(?,?,?)",
            (rid, u["id"], "reopen"),
        )
    return {"id": rid, "status": "reopened"}
