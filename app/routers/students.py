import csv, io, os, secrets, tempfile, zipfile, shutil, hashlib, re, smtplib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from openpyxl import load_workbook
from pwdlib import PasswordHash
import jwt
from app import database
from app.email import send_student_invitation
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
    BulkStudentsIn,
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
MAX_STUDENT_IMPORT_BYTES = 5 * 1024 * 1024


def normalize_student(item):
    email = (item.email or "").strip().casefold()
    username = (item.username or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, f"Invalid student email address: {email}")
    if not email and "@" in username:
        email = username.casefold()
    login = email or username
    display_name = item.display_name.strip()
    if not login or not display_name:
        raise HTTPException(422, "Each student needs an email address and display name")
    return {"email": email or None, "username": login, "display_name": display_name}


def new_invitation(c, student_id):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    c.execute("DELETE FROM student_invitations WHERE student_id=?", (student_id,))
    c.execute(
        "INSERT INTO student_invitations(token_hash,student_id,expires_at) VALUES(?,?,?)",
        (token_hash, student_id, expires_at),
    )
    return token


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
        email = (
            x.email.strip().casefold()
            if x.email is not None
            else c.execute("SELECT email FROM students WHERE id=?", (student_id,)).fetchone()["email"]
        )
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise HTTPException(422, "Enter a valid email address")
        if email:
            if c.execute(
                "SELECT 1 FROM students WHERE email=? COLLATE NOCASE AND id<>?",
                (email, student_id),
            ).fetchone():
                raise HTTPException(409, "That email address is already assigned to another student")
            account = c.execute(
                "SELECT id FROM users WHERE student_id=?", (student_id,)
            ).fetchone()
            collision = c.execute(
                "SELECT id FROM users WHERE username=? COLLATE NOCASE AND id<>?",
                (email, account["id"]),
            ).fetchone()
            if collision:
                raise HTTPException(409, "That email address is already used by another account")
            c.execute("UPDATE users SET username=? WHERE id=?", (email, account["id"]))
        c.execute(
            "UPDATE students SET display_name=?,email=? WHERE id=?",
            (display_name, email, student_id),
        )
        return {
            "id": student_id,
            "course_id": course_id,
            "display_name": display_name,
            "email": email,
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
    item = normalize_student(x)
    sid = secrets.token_hex(12)
    credential = secrets.token_urlsafe(24)
    invitation_token = None
    try:
        with database.transaction(immediate=True) as c:
            require_course_access(c, course_id, u, active=True)
            c.execute(
                "INSERT INTO students(id,display_name,email) VALUES(?,?,?)",
                (sid, item["display_name"], item["email"]),
            )
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id,must_change_password) VALUES(?,?,'student',?,1)",
                (item["username"], ph.hash(credential), sid),
            )
            c.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, sid),
            )
            if item["email"]:
                invitation_token = new_invitation(c, sid)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(409, "Student or username already exists")
    invitation_sent = None
    if invitation_token:
        try:
            send_student_invitation(item["email"], item["display_name"], invitation_token)
            invitation_sent = True
        except (OSError, RuntimeError, smtplib.SMTPException):
            invitation_sent = False
    return {
        "id": sid,
        "username": item["username"],
        "email": item["email"],
        "display_name": item["display_name"],
        "invitation_sent": invitation_sent,
        "one_time_credential": credential if not item["email"] else None,
        "must_change_password": True,
    }


@router.post("/api/students/{student_id}/invitation")
def resend_student_invitation(student_id: str, course_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        student = c.execute(
            """
            SELECT s.email,s.display_name
            FROM course_students cs JOIN students s ON s.id=cs.student_id
            WHERE cs.course_id=? AND cs.student_id=?
            """,
            (course_id, student_id),
        ).fetchone()
        if not student:
            raise HTTPException(404, "Student is not enrolled in this course")
        if not student["email"]:
            raise HTTPException(409, "Add an email address before sending an invitation")
        token = new_invitation(c, student_id)
    try:
        send_student_invitation(student["email"], student["display_name"], token)
    except (OSError, RuntimeError, smtplib.SMTPException):
        raise HTTPException(
            502,
            "Invitation email could not be sent. Check Gmail and app URL settings, then retry.",
        )
    return {"ok": True, "email": student["email"]}


@router.post("/api/students/import-spreadsheet")
async def import_student_spreadsheet(
    course_id: int,
    file: UploadFile = File(...),
    u=Depends(instructor),
):
    if Path(file.filename or "").suffix.casefold() != ".xlsx":
        raise HTTPException(415, "Upload an Excel workbook in .xlsx format")
    with database.get_connection() as c:
        require_course_access(c, course_id, u, active=True)

    contents = await file.read(MAX_STUDENT_IMPORT_BYTES + 1)
    if len(contents) > MAX_STUDENT_IMPORT_BYTES:
        raise HTTPException(413, "Spreadsheet must be 5 MB or smaller")

    try:
        workbook = load_workbook(io.BytesIO(contents), read_only=True, data_only=True)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(422, "Could not read the Excel workbook") from exc

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    worksheet = workbook.active
    try:
        for row_number, row in enumerate(worksheet.iter_rows(values_only=True)):
            if row_number > 500:
                raise HTTPException(422, "You can add up to 500 students at once")
            writer.writerow(
                [
                    value.isoformat() if hasattr(value, "isoformat") else str(value or "")
                    for value in row
                ]
            )
    finally:
        workbook.close()
    return {"csv_text": output.getvalue()}


@router.post("/api/students/bulk")
def create_students_bulk(
    x: BulkStudentsIn,
    response: Response,
    course_id: int,
    u=Depends(instructor),
):
    students = [normalize_student(item) for item in x.students]

    usernames: set[str] = set()
    for item in students:
        normalized = item["username"].casefold()
        if normalized in usernames:
            raise HTTPException(
                422,
                f"Duplicate username in bulk request: {item['username']}",
            )
        usernames.add(normalized)

    created = []
    invitation_tokens = []
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        existing_by_normalized = {}
        students_to_reenroll = {}
        for item in students:
            existing = c.execute(
                "SELECT username,student_id,role,is_active FROM users WHERE username=?",
                (item["username"],),
            ).fetchone()
            if existing:
                normalized = item["username"].casefold()
                enrolled = (
                    existing["role"] == "student"
                    and c.execute(
                        "SELECT 1 FROM course_students WHERE course_id=? AND student_id=?",
                        (course_id, existing["student_id"]),
                    ).fetchone()
                )
                if (
                    existing["role"] == "student"
                    and existing["is_active"]
                    and not enrolled
                ):
                    students_to_reenroll[normalized] = existing
                else:
                    existing_by_normalized[normalized] = existing["username"]

        if existing_by_normalized and not x.skip_existing:
            return {
                "confirmation_required": True,
                "existing_usernames": list(existing_by_normalized.values()),
                "skipped_usernames": [],
                "re_enrolled_usernames": [],
                "count": 0,
                "students": [],
            }

        re_enrolled = []
        for item in students:
            normalized = item["username"].casefold()
            if normalized in existing_by_normalized:
                continue
            existing_student = students_to_reenroll.get(normalized)
            if existing_student:
                c.execute(
                    "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                    (course_id, existing_student["student_id"]),
                )
                re_enrolled.append(item["username"])
                continue
            student_id = secrets.token_hex(12)
            credential = secrets.token_urlsafe(24)
            c.execute(
                "INSERT INTO students(id,display_name,email) VALUES(?,?,?)",
                (student_id, item["display_name"], item["email"]),
            )
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id,must_change_password) VALUES(?,?,'student',?,1)",
                (item["username"], ph.hash(credential), student_id),
            )
            c.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, student_id),
            )
            created.append(
                {
                    "id": student_id,
                    "username": item["username"],
                    "email": item["email"],
                    "display_name": item["display_name"],
                    "one_time_credential": credential if not item["email"] else None,
                    "must_change_password": True,
                }
            )
            if item["email"]:
                invitation_tokens.append(
                    (len(created) - 1, new_invitation(c, student_id), item["email"], item["display_name"])
                )
    for student_index, token, email, display_name in invitation_tokens:
        try:
            send_student_invitation(email, display_name, token)
            created[student_index]["invitation_sent"] = True
        except (OSError, RuntimeError, smtplib.SMTPException):
            created[student_index]["invitation_sent"] = False
    response.status_code = 201
    skipped = (
        list(existing_by_normalized.values()) if x.skip_existing else []
    )
    return {
        "confirmation_required": False,
        "existing_usernames": [],
        "skipped_usernames": skipped,
        "re_enrolled_usernames": re_enrolled,
        "count": len(created),
        "students": created,
    }
