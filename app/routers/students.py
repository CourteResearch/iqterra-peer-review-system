import os, secrets, tempfile, zipfile, shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
import jwt
from app import database
from app.course_access import require_course_access
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
    StudentUpdate,
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
def students_list(course_id: int | None = None, u=Depends(instructor)):
    with database.get_connection() as c:
        if course_id is not None:
            require_course_access(c, course_id, u)
            course_filter = "AND cs.course_id=?"
            params = (course_id,)
        else:
            course_filter = "AND cs.course_id IN (SELECT course_id FROM course_instructors WHERE instructor_id=?)"
            params = (u["id"],)
        student_query = f"""
            SELECT s.*,u.username,u.is_active
            FROM course_students cs
            JOIN students s ON s.id=cs.student_id
            LEFT JOIN users u ON u.student_id=s.id
            WHERE 1=1 {course_filter}
            ORDER BY s.display_name
        """
        rows = [dict(r) for r in c.execute(student_query, params)]
        return {
            "items": rows,
            "students": rows,
        }


@router.get("/api/students/{student_id}")
def student_detail(student_id: str, course_id: int, u=Depends(instructor)):
    with database.get_connection() as c:
        require_course_access(c, course_id, u)
        row = c.execute(
            """
            SELECT s.id,s.display_name,u.username,u.is_active,cs.course_id
            FROM course_students cs
            JOIN students s ON s.id=cs.student_id
            LEFT JOIN users u ON u.student_id=s.id
            WHERE cs.course_id=? AND s.id=?
            """,
            (course_id, student_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Student is not enrolled in this course")
        return dict(row)


@router.put("/api/students/{student_id}")
def update_student(
    student_id: str,
    x: StudentUpdate,
    course_id: int,
    u=Depends(instructor),
):
    display_name = x.display_name.strip()
    if not display_name:
        raise HTTPException(422, "Student name cannot be blank")
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        enrolled = c.execute(
            "SELECT 1 FROM course_students WHERE course_id=? AND student_id=?",
            (course_id, student_id),
        ).fetchone()
        if not enrolled:
            raise HTTPException(404, "Student is not enrolled in this course")
        c.execute(
            "UPDATE students SET display_name=? WHERE id=?",
            (display_name, student_id),
        )
        return {
            "id": student_id,
            "course_id": course_id,
            "display_name": display_name,
        }


@router.delete("/api/students/{student_id}", status_code=204)
def remove_student(student_id: str, course_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        if not c.execute(
            "SELECT 1 FROM course_students WHERE course_id=? AND student_id=?",
            (course_id, student_id),
        ).fetchone():
            raise HTTPException(404, "Student is not enrolled in this course")
        if c.execute(
            """
            SELECT 1 FROM submissions sub
            JOIN assignments a ON a.id=sub.assignment_id
            WHERE a.course_id=? AND sub.student_id=? AND sub.is_submitted=1 LIMIT 1
            """,
            (course_id, student_id),
        ).fetchone():
            raise HTTPException(
                409,
                "Student has submitted work; preserve that submission history instead of removing enrollment",
            )
        if c.execute(
            """
            SELECT 1 FROM allocations al
            JOIN assignments a ON a.id=al.assignment_id
            WHERE a.course_id=? AND al.reviewer_id=? LIMIT 1
            """,
            (course_id, student_id),
        ).fetchone():
            raise HTTPException(
                409,
                "Student has assigned reviews; preserve review history instead of removing enrollment",
            )
        c.execute(
            "DELETE FROM course_students WHERE course_id=? AND student_id=?",
            (course_id, student_id),
        )
        return None


@router.post("/api/students", status_code=201)
def create_student(x: StudentIn, course_id: int, u=Depends(instructor)):
    sid = secrets.token_hex(12)
    credential = secrets.token_urlsafe(24)
    try:
        with database.transaction(immediate=True) as c:
            require_course_access(c, course_id, u, active=True)
            c.execute(
                "INSERT INTO students(id,display_name) VALUES(?,?)",
                (sid, x.display_name),
            )
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id,must_change_password) VALUES(?,?,'student',?,1)",
                (x.username, ph.hash(credential), sid),
            )
            c.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, sid),
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(409, "Student or username already exists")
    return {
        "id": sid,
        "username": x.username,
        "display_name": x.display_name,
        "one_time_credential": credential,
        "must_change_password": True,
    }
