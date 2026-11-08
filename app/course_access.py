from fastapi import HTTPException


def require_course_access(connection, course_id, user, *, active=False):
    course = connection.execute(
        "SELECT * FROM courses WHERE id=?", (course_id,)
    ).fetchone()
    if not course:
        raise HTTPException(404, "Course not found")
    if user["role"] == "instructor":
        access = connection.execute(
            "SELECT 1 FROM course_instructors WHERE course_id=? AND instructor_id=?",
            (course_id, user["id"]),
        ).fetchone()
    else:
        access = connection.execute(
            "SELECT 1 FROM course_students WHERE course_id=? AND student_id=?",
            (course_id, user["student_id"]),
        ).fetchone()
    if not access:
        raise HTTPException(403, "You do not have access to this course")
    if active and course["is_archived"]:
        raise HTTPException(409, "This course is archived")
    return course


def require_assignment_access(connection, assignment_id, user, *, active=False):
    assignment = connection.execute(
        "SELECT * FROM assignments WHERE id=?", (assignment_id,)
    ).fetchone()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if assignment["course_id"] is None:
        raise HTTPException(409, "Assignment is not associated with a course")
    course = require_course_access(
        connection, assignment["course_id"], user, active=active
    )
    return assignment, course
