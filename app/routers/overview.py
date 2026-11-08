import os, secrets, tempfile, zipfile, shutil
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
from app.helpers import questions
from app.course_access import require_assignment_access
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


def assignment(c, r):
    d = dict(r)
    d["questions"] = questions(c, r["id"])
    return d


@router.get("/api/overview")
def overview(assignment_id: int, u=Depends(instructor)):
    with database.get_connection() as c:
        a, course = require_assignment_access(c, assignment_id, u)
        students_data = []
        for s in c.execute(
            "SELECT s.id,s.display_name FROM students s JOIN course_students cs ON cs.student_id=s.id WHERE cs.course_id=? ORDER BY s.display_name",
            (course["id"],),
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
            settings = json.loads(q["settings"])
            response_details = []
            if q["recipient"] == "peer" and q["question_type"] != "points":
                response_rows = c.execute(
                    """
                    SELECT qa.answer_json,reviewer.display_name respondent
                    FROM question_answers qa
                    JOIN reviews r ON r.id=qa.review_id
                    JOIN allocations a ON a.id=r.allocation_id
                    JOIN students reviewer ON reviewer.id=a.reviewer_id
                    WHERE a.assignment_id=? AND qa.question_id=? AND r.status='submitted'
                    ORDER BY r.submitted_at,r.id
                    """,
                    (assignment_id, q["id"]),
                ).fetchall()
                if not response_rows:
                    vals = [
                        row["score"]
                        for row in c.execute(
                            """
                            SELECT ra.score FROM review_answers ra
                            JOIN reviews r ON r.id=ra.review_id
                            JOIN allocations a ON a.id=r.allocation_id
                            WHERE a.assignment_id=? AND ra.question_id=?
                              AND r.status='submitted'
                            """,
                            (assignment_id, q["id"]),
                        )
                    ]
                else:
                    vals = [json.loads(row["answer_json"]) for row in response_rows]
                    response_details = [
                        {
                            "respondent": row["respondent"],
                            "value": json.loads(row["answer_json"]),
                        }
                        for row in response_rows
                    ]
            else:
                vals = []
            if q["recipient"] == "peer" and q["question_type"] != "points":
                response_count = len(vals)
            else:
                response_count = c.execute(
                    """
                    SELECT COUNT(*) FROM assignment_form_answers
                    WHERE assignment_id=? AND question_id=?
                    """,
                    (assignment_id, q["id"]),
                ).fetchone()[0]
                peer_names = (
                    {
                        peer["id"]: peer["display_name"]
                        for peer in c.execute(
                            """
                            SELECT s.id,s.display_name FROM students s
                            JOIN course_students cs ON cs.student_id=s.id
                            WHERE cs.course_id=?
                            """,
                            (course["id"],),
                        )
                    }
                    if q["question_type"] == "points"
                    else {}
                )
                for row in c.execute(
                    """
                    SELECT fa.answer_json,student.display_name,group_row.name group_name
                    FROM assignment_form_answers fa
                    JOIN students student ON student.id=fa.respondent_id
                    LEFT JOIN course_groups group_row
                      ON fa.recipient_key='group:' || group_row.id
                    WHERE fa.assignment_id=? AND fa.question_id=?
                    ORDER BY fa.submitted_at,fa.respondent_id
                    """,
                    (assignment_id, q["id"]),
                ):
                    value = json.loads(row["answer_json"])
                    if q["question_type"] == "points" and isinstance(value, dict):
                        value = {
                            peer_names.get(peer_id, peer_id): points
                            for peer_id, points in value.items()
                        }
                    response_details.append(
                        {
                            "respondent": row["group_name"] or row["display_name"],
                            "value": value,
                        }
                    )
            labels = settings.get("labels", [])
            dist = (
                {str(i): 0 for i in range(1, len(labels) + 1)}
                if q["question_type"] == "rubric"
                else {}
            )
            if q["question_type"] == "rubric":
                for value in vals:
                    dist[str(value)] = dist.get(str(value), 0) + 1
            outcomes.append(
                {
                    "question_id": q["id"],
                    "prompt": q["prompt"],
                    "type": q["question_type"],
                    "recipient": q["recipient"],
                    "settings": settings,
                    "responses": response_count,
                    "response_details": response_details,
                    "average_score": (
                        sum(vals) / len(vals)
                        if vals and q["question_type"] in ("rubric", "contribution")
                        else None
                    ),
                    "distribution": dist,
                }
            )
        return {
            "assignment": assignment(c, a),
            "students": students_data,
            "total_students": c.execute(
                "SELECT COUNT(*) FROM course_students WHERE course_id=?",
                (course["id"],),
            ).fetchone()[0],
            "total_reviews": total,
            "completed_reviews": complete,
            "pending_reviews": total - complete,
            "moderation_count": c.execute(
                "SELECT COUNT(*) FROM review_flags f JOIN reviews r ON r.id=f.review_id JOIN allocations a ON a.id=r.allocation_id WHERE a.assignment_id=? AND f.status='open'",
                (assignment_id,),
            ).fetchone()[0],
            "question_outcomes": outcomes,
        }
