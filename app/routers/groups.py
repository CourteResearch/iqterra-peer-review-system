import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import database
from app.course_access import require_course_access
from app.schemas import CourseGroupIn, GroupMemberIn
from app.security import instructor

router = APIRouter()


def _group(c, group_id, user, *, active=False):
    group = c.execute(
        "SELECT * FROM course_groups WHERE id=?", (group_id,)
    ).fetchone()
    if not group:
        raise HTTPException(404, "Group not found")
    require_course_access(c, group["course_id"], user, active=active)
    if active and group["is_archived"]:
        raise HTTPException(409, "This group is archived")
    return group


def _ensure_membership_editable(c, group):
    if c.execute(
        """
        SELECT 1 FROM assignments a
        JOIN allocations al ON al.assignment_id=a.id
        WHERE a.course_id=? AND a.group_mode='within_group' LIMIT 1
        """,
        (group["course_id"],),
    ).fetchone():
        raise HTTPException(
            409,
            "Group membership is locked after within-group review allocations are generated",
        )


@router.get("/api/groups")
def list_groups(course_id: int, include_archived: bool = False, u=Depends(instructor)):
    with database.get_connection() as c:
        require_course_access(c, course_id, u)
        groups = []
        for group in c.execute(
            """
            SELECT g.*,COUNT(gm.student_id) member_count
            FROM course_groups g LEFT JOIN course_group_members gm ON gm.group_id=g.id
            WHERE g.course_id=? AND (? OR g.is_archived=0)
            GROUP BY g.id ORDER BY g.is_archived,g.name COLLATE NOCASE
            """,
            (course_id, int(include_archived)),
        ):
            item = dict(group)
            item["members"] = [
                dict(student)
                for student in c.execute(
                    """
                    SELECT s.id,s.display_name,u.username
                    FROM course_group_members gm
                    JOIN students s ON s.id=gm.student_id
                    LEFT JOIN users u ON u.student_id=s.id
                    WHERE gm.group_id=? ORDER BY s.display_name COLLATE NOCASE
                    """,
                    (group["id"],),
                )
            ]
            groups.append(item)
        return {"items": groups}


@router.post("/api/courses/{course_id}/groups", status_code=201)
def create_group(course_id: int, x: CourseGroupIn, u=Depends(instructor)):
    name = x.name.strip()
    if not name:
        raise HTTPException(422, "Group name cannot be blank")
    try:
        with database.transaction(immediate=True) as c:
            require_course_access(c, course_id, u, active=True)
            group_id = c.execute(
                "INSERT INTO course_groups(course_id,name,description) VALUES(?,?,?)",
                (course_id, name, x.description.strip()),
            ).lastrowid
            return dict(
                c.execute("SELECT * FROM course_groups WHERE id=?", (group_id,)).fetchone()
            )
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(409, "A group with that name already exists in this course")
        raise


@router.put("/api/groups/{group_id}")
def update_group(group_id: int, x: CourseGroupIn, u=Depends(instructor)):
    name = x.name.strip()
    if not name:
        raise HTTPException(422, "Group name cannot be blank")
    try:
        with database.transaction(immediate=True) as c:
            group = _group(c, group_id, u, active=True)
            c.execute(
                "UPDATE course_groups SET name=?,description=? WHERE id=?",
                (name, x.description.strip(), group_id),
            )
            return dict(
                c.execute("SELECT * FROM course_groups WHERE id=?", (group_id,)).fetchone()
            )
    except sqlite3.IntegrityError as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(409, "A group with that name already exists in this course")
        raise


@router.post("/api/groups/{group_id}/archive")
def archive_group(group_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        group = _group(c, group_id, u)
        _ensure_membership_editable(c, group)
        c.execute("UPDATE course_groups SET is_archived=1 WHERE id=?", (group_id,))
        return {"ok": True, "is_archived": True}


@router.post("/api/groups/{group_id}/restore")
def restore_group(group_id: int, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        _group(c, group_id, u)
        c.execute("UPDATE course_groups SET is_archived=0 WHERE id=?", (group_id,))
        return {"ok": True, "is_archived": False}


@router.post("/api/groups/{group_id}/members", status_code=201)
def add_member(group_id: int, x: GroupMemberIn, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        group = _group(c, group_id, u, active=True)
        _ensure_membership_editable(c, group)
        if not c.execute(
            "SELECT 1 FROM course_students WHERE course_id=? AND student_id=?",
            (group["course_id"], x.student_id),
        ).fetchone():
            raise HTTPException(404, "Student is not enrolled in this course")
        c.execute(
            """
            INSERT INTO course_group_members(course_id,group_id,student_id)
            VALUES(?,?,?)
            ON CONFLICT(course_id,student_id) DO UPDATE SET group_id=excluded.group_id
            """,
            (group["course_id"], group_id, x.student_id),
        )
        return {"ok": True, "group_id": group_id, "student_id": x.student_id}


@router.delete("/api/groups/{group_id}/members/{student_id}")
def remove_member(group_id: int, student_id: str, u=Depends(instructor)):
    with database.transaction(immediate=True) as c:
        group = _group(c, group_id, u)
        _ensure_membership_editable(c, group)
        result = c.execute(
            "DELETE FROM course_group_members WHERE group_id=? AND student_id=?",
            (group_id, student_id),
        )
        if not result.rowcount:
            raise HTTPException(404, "Student is not a member of this group")
        return {"ok": True}
