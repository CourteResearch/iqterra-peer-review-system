import secrets

from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash

from app import database
from app.course_access import require_course_access
from app.schemas import CourseIn, CourseInstructorIn, CourseStudentIn
from app.security import current_user, instructor

router = APIRouter()
password_hash = PasswordHash.recommended()


@router.get("/api/courses")
def list_courses(include_archived: bool = False, u=Depends(current_user)):
    with database.get_connection() as c:
        if u["role"] == "instructor":
            rows = c.execute(
                """
                SELECT c.*, COUNT(DISTINCT cs.student_id) student_count,
                       COUNT(DISTINCT ci.instructor_id) instructor_count
                FROM courses c
                JOIN course_instructors mine ON mine.course_id=c.id
                LEFT JOIN course_students cs ON cs.course_id=c.id
                LEFT JOIN course_instructors ci ON ci.course_id=c.id
                WHERE mine.instructor_id=? AND (? OR c.is_archived=0)
                GROUP BY c.id ORDER BY c.is_archived, c.title
                """,
                (u["id"], int(include_archived)),
            )
        else:
            rows = c.execute(
                """
                SELECT c.*, COUNT(DISTINCT cs.student_id) student_count,
                       COUNT(DISTINCT ci.instructor_id) instructor_count
                FROM courses c
                JOIN course_students mine ON mine.course_id=c.id
                LEFT JOIN course_students cs ON cs.course_id=c.id
                LEFT JOIN course_instructors ci ON ci.course_id=c.id
                WHERE mine.student_id=? AND (? OR c.is_archived=0)
                GROUP BY c.id ORDER BY c.is_archived, c.title
                """,
                (u["student_id"], int(include_archived)),
            )
        return {"items": [dict(row) for row in rows]}


@router.post("/api/courses", status_code=201)
def create_course(x: CourseIn, u=Depends(instructor)):
    title = x.title.strip()
    if not title:
        raise HTTPException(422, "Course name cannot be blank")
    with database.transaction(immediate=True) as c:
        course_id = c.execute(
            "INSERT INTO courses(title,code,term,description,created_by) VALUES(?,?,?,?,?)",
            (title, x.code.strip(), x.term.strip(), x.description.strip(), u["id"]),
        ).lastrowid
        c.execute(
            "INSERT INTO course_instructors(course_id,instructor_id) VALUES(?,?)",
            (course_id, u["id"]),
        )
        return dict(c.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())


@router.get("/api/courses/{course_id}")
def get_course(course_id: int, u=Depends(current_user)):
    with database.get_connection() as c:
        course = require_course_access(c, course_id, u)
        instructors = [
            dict(row)
            for row in c.execute(
                """
                SELECT u.id,u.username,COALESCE(s.display_name,u.username) display_name
                FROM course_instructors ci JOIN users u ON u.id=ci.instructor_id
                LEFT JOIN students s ON s.id=u.student_id
                WHERE ci.course_id=? ORDER BY display_name
                """,
                (course_id,),
            )
        ]
        return {**dict(course), "instructors": instructors}


@router.put("/api/courses/{course_id}")
def update_course(course_id: int, x: CourseIn, u=Depends(instructor)):
    title = x.title.strip()
    if not title:
        raise HTTPException(422, "Course name cannot be blank")
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        c.execute(
            "UPDATE courses SET title=?,code=?,term=?,description=? WHERE id=?",
            (title, x.code.strip(), x.term.strip(), x.description.strip(), course_id),
        )
        return dict(c.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())


@router.delete("/api/courses/{course_id}", status_code=204)
def delete_course(course_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u)
        if c.execute(
            "SELECT 1 FROM assignments WHERE course_id=? LIMIT 1", (course_id,)
        ).fetchone():
            raise HTTPException(
                409,
                "Course has assignments and history; archive it instead of deleting it",
            )
        c.execute("DELETE FROM courses WHERE id=?", (course_id,))
        return None


@router.post("/api/courses/{course_id}/archive")
def archive_course(course_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u)
        c.execute("UPDATE courses SET is_archived=1 WHERE id=?", (course_id,))
        return {"ok": True, "is_archived": True}


@router.post("/api/courses/{course_id}/restore")
def restore_course(course_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u)
        c.execute("UPDATE courses SET is_archived=0 WHERE id=?", (course_id,))
        return {"ok": True, "is_archived": False}


@router.post("/api/courses/{course_id}/instructors", status_code=201)
def add_instructor(course_id: int, x: CourseInstructorIn, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        account = c.execute(
            "SELECT id,role FROM users WHERE username=? COLLATE NOCASE AND is_active=1",
            (x.username.strip(),),
        ).fetchone()
        if not account or account["role"] != "instructor":
            raise HTTPException(404, "Active instructor account not found")
        c.execute(
            "INSERT OR IGNORE INTO course_instructors(course_id,instructor_id) VALUES(?,?)",
            (course_id, account["id"]),
        )
        return {"ok": True}


@router.post("/api/courses/{course_id}/students", status_code=201)
def enroll_student(course_id: int, x: CourseStudentIn, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        require_course_access(c, course_id, u, active=True)
        account = c.execute(
            "SELECT student_id,role FROM users WHERE username=? COLLATE NOCASE AND is_active=1",
            (x.username.strip(),),
        ).fetchone()
        if not account or account["role"] != "student":
            raise HTTPException(404, "Active student account not found")
        c.execute(
            "INSERT OR IGNORE INTO course_students(course_id,student_id) VALUES(?,?)",
            (course_id, account["student_id"]),
        )
        return {"ok": True}
