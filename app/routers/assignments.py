import os, secrets, tempfile, zipfile, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
from app.course_access import require_assignment_access, require_course_access
from app.allocation import allocate_group_reviews, allocate_reviews
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
def get_assignments(course_id: int | None = None, u=Depends(current_user)):
    with database.get_connection() as c:
        if u["role"] == "student":
            if course_id is not None:
                require_course_access(c, course_id, u)
            query = """
                SELECT a.*,
                       s.id own_submission_id,
                       s.title own_submission_title,
                       s.content own_submission_content,
                       s.file_name own_submission_file_name,
                       s.original_file_name own_submission_original_file_name,
                       s.is_submitted own_submission_is_submitted,
                       EXISTS(
                           SELECT 1 FROM allocations al
                           WHERE al.submission_id=s.id
                       ) own_submission_allocated
                FROM assignments a
                JOIN courses co ON co.id=a.course_id
                JOIN course_students cs ON cs.course_id=co.id
                LEFT JOIN submissions s
                  ON s.assignment_id=a.id AND s.student_id=cs.student_id
                WHERE cs.student_id=? AND co.is_archived=0
                  AND a.status IN ('open','closed')
            """
            params = [u["student_id"]]
            if course_id is not None:
                query += " AND a.course_id=?"
                params.append(course_id)
            query += " ORDER BY a.due_at,a.id DESC"
            rows = c.execute(query, params)
            items = []
            for row in rows:
                item = assignment(c, row)
                item["my_submission"] = None
                if row["own_submission_id"] is not None:
                    item["my_submission"] = {
                        "id": row["own_submission_id"],
                        "title": row["own_submission_title"],
                        "content": row["own_submission_content"],
                        "is_submitted": bool(row["own_submission_is_submitted"]),
                        "locked": bool(
                            row["own_submission_is_submitted"]
                            and row["own_submission_allocated"]
                        ),
                        "original_file_name": row[
                            "own_submission_original_file_name"
                        ],
                        **(
                            {
                                "file_url": (
                                    f"/api/submissions/{row['own_submission_id']}/file"
                                )
                            }
                            if row["own_submission_file_name"]
                            else {}
                        ),
                    }
                items.append(item)
            return items
        if course_id is not None:
            require_course_access(c, course_id, u)
            rows = c.execute(
                """
                SELECT a.* FROM assignments a
                WHERE a.course_id=?
                ORDER BY (SELECT COUNT(*) FROM allocations x WHERE x.assignment_id=a.id) DESC,
                         a.id DESC
                """,
                (course_id,),
            )
        elif u["role"] == "instructor":
            rows = c.execute(
                """
                SELECT a.* FROM assignments a
                JOIN course_instructors ci ON ci.course_id=a.course_id
                WHERE ci.instructor_id=?
                ORDER BY (SELECT COUNT(*) FROM allocations x WHERE x.assignment_id=a.id) DESC,
                         a.id DESC
                """,
                (u["id"],),
            )
        return [
            assignment(c, r)
            for r in rows
        ]


@router.post("/api/assignments", status_code=201)
def create_assignment(x: AssignmentIn, u=Depends(instructor)):
    if x.course_id is None:
        raise HTTPException(422, "A course is required")
    qs = x.questions or [{"prompt": p, "order": i + 1} for i, p in enumerate(PROMPTS)]
    if len(qs) != 5:
        raise HTTPException(422, "Exactly five questions are required")
    with database.transaction(immediate=True) as c:
        require_course_access(c, x.course_id, u, active=True)
        aid = c.execute(
            "INSERT INTO assignments(title,instructions,due_at,course_id,group_mode) VALUES(?,?,?,?,?)",
            (x.title, x.instructions, x.due_at, x.course_id, x.group_mode),
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
        r, _ = require_assignment_access(c, aid, u)
        return assignment(c, r)


@router.put("/api/assignments/{aid}")
def update_assignment(aid: int, x: AssignmentIn, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        r, _ = require_assignment_access(c, aid, u, active=True)
        if (
            x.group_mode != r["group_mode"]
            and c.execute(
                "SELECT 1 FROM allocations WHERE assignment_id=? LIMIT 1", (aid,)
            ).fetchone()
        ):
            raise HTTPException(
                409, "Review group mode cannot change after allocations are generated"
            )
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
            "UPDATE assignments SET title=?,instructions=?,due_at=?,group_mode=? WHERE id=?",
            (x.title, x.instructions, x.due_at, x.group_mode, aid),
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


@router.delete("/api/assignments/{aid}", status_code=204)
def delete_assignment(aid: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_assignment_access(c, aid, u, active=True)
        if c.execute(
            "SELECT 1 FROM submissions WHERE assignment_id=? LIMIT 1", (aid,)
        ).fetchone():
            raise HTTPException(
                409,
                "Assignment has submissions or review history; close it instead of deleting it",
            )
        c.execute("DELETE FROM assignments WHERE id=?", (aid,))
        return None


@router.post("/api/assignments/{aid}/allocations")
def alloc(aid: int, x: AllocationIn = AllocationIn(), u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_assignment_access(c, aid, u, active=True)
        if c.execute(
            "SELECT 1 FROM allocations WHERE assignment_id=?", (aid,)
        ).fetchone():
            raise HTTPException(409, "Allocations already exist")
        assignment_row = c.execute(
            "SELECT group_mode,course_id FROM assignments WHERE id=?", (aid,)
        ).fetchone()
        roster = c.execute(
            "SELECT student_id FROM course_students WHERE course_id=? ORDER BY student_id",
            (assignment_row["course_id"],),
        ).fetchall()
        if not roster:
            raise HTTPException(422, "Enroll students in this course before allocating reviews")
        c.executemany(
            """
            INSERT OR IGNORE INTO submissions(
                assignment_id,student_id,title,content,is_submitted
            ) VALUES(?,?, 'Pending submission', '', 0)
            """,
            [(aid, row["student_id"]) for row in roster],
        )
        if assignment_row["group_mode"] == "within_group":
            ungrouped_students = c.execute(
                """
                SELECT s.display_name
                FROM course_students cs
                JOIN students s ON s.id=cs.student_id
                LEFT JOIN course_group_members gm
                  ON gm.course_id=cs.course_id AND gm.student_id=cs.student_id
                LEFT JOIN course_groups g
                  ON g.id=gm.group_id AND g.is_archived=0
                WHERE cs.course_id=? AND g.id IS NULL
                ORDER BY s.display_name COLLATE NOCASE
                """,
                (assignment_row["course_id"],),
            ).fetchall()
            if ungrouped_students:
                names = ", ".join(row["display_name"] for row in ungrouped_students)
                raise HTTPException(
                    422,
                    f"Create active groups and assign every enrolled student to an active team before allocating within-team reviews: {names}",
                )
            group_rows = c.execute(
                """
                SELECT sub.id submission_id,sub.student_id,g.id group_id,g.name group_name
                FROM submissions sub
                LEFT JOIN course_group_members gm
                    ON gm.student_id=sub.student_id AND gm.course_id=?
                LEFT JOIN course_groups g
                    ON g.id=gm.group_id AND g.is_archived=0
                WHERE sub.assignment_id=?
                ORDER BY g.name COLLATE NOCASE,sub.student_id
                """,
                (assignment_row["course_id"], aid),
            ).fetchall()
            ungrouped = [row for row in group_rows if row["group_id"] is None]
            if ungrouped:
                raise HTTPException(
                    422,
                    "Create active groups and assign every submitting student to one before allocating within-group reviews",
                )
            cohorts = {}
            for row in group_rows:
                cohorts.setdefault(row["group_id"], []).append(
                    (row["student_id"], row["submission_id"])
                )
            group_reviewers = {}
            for row in c.execute(
                """
                SELECT gm.group_id,gm.student_id
                FROM course_group_members gm
                JOIN course_groups g ON g.id=gm.group_id AND g.is_archived=0
                JOIN course_students cs
                  ON cs.course_id=gm.course_id AND cs.student_id=gm.student_id
                WHERE gm.course_id=?
                ORDER BY gm.group_id,gm.student_id
                """,
                (assignment_row["course_id"],),
            ):
                group_reviewers.setdefault(row["group_id"], []).append(row["student_id"])
        else:
            subs = c.execute(
                "SELECT id,student_id FROM submissions WHERE assignment_id=? ORDER BY student_id",
                (aid,),
            ).fetchall()
            cohorts = {None: [(row["student_id"], row["id"]) for row in subs]}
            group_reviewers = {}

        if not any(cohorts.values()):
            raise HTTPException(422, "Submit student work before allocating reviews")

        if x.mode == "automatic":
            pairs = []
            group_names = (
                {row["group_id"]: row["group_name"] for row in group_rows}
                if assignment_row["group_mode"] == "within_group"
                else {}
            )
            try:
                for group_id, members in cohorts.items():
                    if assignment_row["group_mode"] == "within_group":
                        pairs.extend(
                            allocate_group_reviews(
                                group_reviewers.get(group_id, []),
                                members,
                                x.reviewers_per_submission,
                            )
                        )
                    else:
                        cohort_pairs = allocate_reviews(
                            [student_id for student_id, _ in members],
                            x.reviewers_per_submission,
                        )
                        submission_ids = dict(members)
                        pairs.extend(
                            (reviewer, submission_ids[student_id])
                            for reviewer, student_id in cohort_pairs
                        )
            except ValueError as e:
                group_name = group_names.get(group_id)
                detail = (
                    f"Group '{group_name}' cannot support this review allocation: {e}"
                    if group_name
                    else str(e)
                )
                raise HTTPException(422, detail)
        else:
            submission_cohort = {
                submission_id: (group_id, dict(members))
                for group_id, members in cohorts.items()
                for _, submission_id in members
            }
            owner_by_submission = {
                submission_id: student_id
                for members in cohorts.values()
                for student_id, submission_id in members
            }
            submission_by_student = {
                student_id: submission_id
                for submission_id, student_id in owner_by_submission.items()
            }
            submitted = {}
            for item in x.assignments:
                if (item.submission_id is None) == (item.student_id is None):
                    raise HTTPException(
                        422,
                        "Each manual allocation must identify exactly one target student or submission",
                    )
                submission_id = (
                    item.submission_id
                    if item.submission_id is not None
                    else submission_by_student.get(item.student_id)
                )
                if submission_id is None or submission_id in submitted:
                    raise HTTPException(
                        422,
                        "Manual allocation targets must identify each student exactly once",
                    )
                submitted[submission_id] = item
            target_ids = set(submission_cohort)
            if set(submitted) != target_ids:
                raise HTTPException(
                    422,
                    "Manual allocation must include each submitted work exactly once",
                )
            pairs = []
            loads = {
                group_id: {
                    student_id: 0
                    for student_id in (
                        group_reviewers.get(group_id, [])
                        if assignment_row["group_mode"] == "within_group"
                        else [student_id for student_id, _ in members]
                    )
                }
                for group_id, members in cohorts.items()
            }
            for submission_id, (group_id, members) in submission_cohort.items():
                reviewer_ids = submitted[submission_id].reviewer_ids
                if len(reviewer_ids) != x.reviewers_per_submission:
                    raise HTTPException(
                        422,
                        f"Each submission must have exactly {x.reviewers_per_submission} reviewers",
                    )
                if len(set(reviewer_ids)) != len(reviewer_ids):
                    raise HTTPException(
                        422, "A reviewer cannot be assigned twice to the same submission"
                    )
                owner = owner_by_submission[submission_id]
                if owner in reviewer_ids:
                    raise HTTPException(422, "Students cannot review their own submissions")
                eligible_reviewers = (
                    set(group_reviewers.get(group_id, []))
                    if assignment_row["group_mode"] == "within_group"
                    else set(members)
                )
                if any(reviewer_id not in eligible_reviewers for reviewer_id in reviewer_ids):
                    raise HTTPException(
                        422,
                        "Manual reviewers must be enrolled in the same active review group",
                    )
                pairs.extend((reviewer_id, submission_id) for reviewer_id in reviewer_ids)
                for reviewer_id in reviewer_ids:
                    loads[group_id][reviewer_id] += 1

            student_pairs = {
                (reviewer_id, owner_by_submission[submission_id])
                for reviewer_id, submission_id in pairs
            }
            reciprocal_pairs = [
                (reviewer_id, submission_id)
                for reviewer_id, submission_id in pairs
                if (owner_by_submission[submission_id], reviewer_id) in student_pairs
            ]
            if assignment_row["group_mode"] == "within_group":
                reciprocal_size = {
                    group_id: len(group_reviewers.get(group_id, []))
                    for group_id in cohorts
                }
            else:
                reciprocal_size = {
                    group_id: len(members) for group_id, members in cohorts.items()
                }
            if any(
                reciprocal_size[submission_cohort[submission_id][0]] != 2
                for _, submission_id in reciprocal_pairs
            ):
                raise HTTPException(422, "Reciprocal reviews are not allowed")

            for reviewer_loads in loads.values():
                if (
                    reviewer_loads
                    and max(reviewer_loads.values()) - min(reviewer_loads.values()) > 1
                ):
                    raise HTTPException(
                        422,
                        "Manual allocation must distribute review workloads as evenly as possible within each review group",
                    )
        c.executemany(
            "INSERT INTO allocations(assignment_id,reviewer_id,submission_id) VALUES(?,?,?)",
            [(aid, rv, submission_id) for rv, submission_id in pairs],
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
        require_assignment_access(c, assignment_id, u)
        return {
            "items": [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM allocations WHERE assignment_id=?", (assignment_id,)
                )
            ],
            "submissions": [
                dict(row)
                for row in c.execute(
                    """
                    SELECT sub.id,cs.student_id,s.display_name student_name,
                           g.id group_id,g.name group_name,
                           COALESCE(sub.is_submitted,0) is_submitted
                    FROM assignments a
                    JOIN course_students cs ON cs.course_id=a.course_id
                    JOIN students s ON s.id=cs.student_id
                    LEFT JOIN submissions sub
                      ON sub.assignment_id=a.id AND sub.student_id=cs.student_id
                    LEFT JOIN course_group_members gm
                        ON gm.student_id=cs.student_id AND gm.course_id=a.course_id
                    LEFT JOIN course_groups g
                        ON g.id=gm.group_id AND g.is_archived=0
                    WHERE a.id=?
                    ORDER BY s.display_name COLLATE NOCASE
                    """,
                    (assignment_id,),
                )
            ],
            "reviewers": [
                dict(row)
                for row in c.execute(
                    """
                    SELECT s.id student_id,s.display_name,g.id group_id,g.name group_name
                    FROM course_students cs
                    JOIN students s ON s.id=cs.student_id
                    JOIN assignments a ON a.course_id=cs.course_id
                    LEFT JOIN course_group_members gm
                      ON gm.course_id=cs.course_id AND gm.student_id=cs.student_id
                    LEFT JOIN course_groups g
                      ON g.id=gm.group_id AND g.is_archived=0
                    WHERE a.id=?
                    ORDER BY s.display_name COLLATE NOCASE
                    """,
                    (assignment_id,),
                )
            ],
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
        a, _ = require_assignment_access(c, aid, u, active=True)
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
        with database.get_connection() as c:
            existing_file = c.execute(
                """
                SELECT s.file_name FROM submissions s
                WHERE s.assignment_id=? AND s.student_id=?
                """,
                (aid, u["student_id"]),
            ).fetchone()
        if not existing_file or not existing_file["file_name"]:
            raise HTTPException(422, "Provide text or an attachment")
    old_file = None
    with database.transaction(immediate=True) as c:
        live_assignment = c.execute(
            "SELECT status,due_at FROM assignments WHERE id=?", (aid,)
        ).fetchone()
        if not live_assignment:
            raise HTTPException(404, "Assignment not found")
        require_assignment_access(c, aid, u, active=True)
        if live_assignment["status"] != "open" or due_passed(live_assignment["due_at"]):
            raise HTTPException(409, "Assignment is closed or past due")
        old = c.execute(
            "SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",
            (aid, u["student_id"]),
        ).fetchone()
        if (
            old
            and old["is_submitted"]
            and c.execute(
                "SELECT 1 FROM allocations WHERE submission_id=?", (old["id"],)
            ).fetchone()
        ):
            raise HTTPException(409, "Submission locked after allocation")
        filename = old["file_name"] if old else None
        original_filename = old["original_file_name"] if old else None
        if old and old["file_name"]:
            old_file = old["file_name"]
        if data:
            filename = secrets.token_hex(20) + ext
            original_filename = file.filename
            folder = database.DATA_DIR / "uploads"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / filename).write_bytes(data)
        if old:
            c.execute(
                "UPDATE submissions SET title=?,content=?,file_name=?,original_file_name=?,is_submitted=1,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title, content, filename, original_filename, old["id"]),
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
    return {
        "id": sid,
        "assignment_id": aid,
        "title": title,
        "content": content,
        "is_submitted": True,
        "file_url": f"/api/submissions/{sid}/file" if filename else None,
    }


@router.get("/api/submissions/{sid}/file")
def file(sid: int, u=Depends(current_user)):
    with database.get_connection() as c:
        r = c.execute(
            "SELECT s.*,a.course_id, EXISTS(SELECT 1 FROM allocations x WHERE x.submission_id=s.id AND x.reviewer_id=?) assigned FROM submissions s JOIN assignments a ON a.id=s.assignment_id WHERE s.id=?",
            (u["student_id"] if u["role"] == "student" else "", sid),
        ).fetchone()
        if not r:
            raise HTTPException(404, "Submission not found")
        if (
            u["role"] == "student"
            and u["student_id"] != r["student_id"]
            and not r["assigned"]
        ):
            raise HTTPException(403, "Not authorized")
        require_course_access(c, r["course_id"], u)
        if not r["file_name"]:
            raise HTTPException(404, "No file")
        base = (database.DATA_DIR / "uploads").resolve()
        p = (base / Path(r["file_name"]).name).resolve()
        if p.parent != base or not p.is_file():
            raise HTTPException(404, "File missing")
        return FileResponse(p, filename="submission" + p.suffix.lower())
