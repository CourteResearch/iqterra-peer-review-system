"""Non-destructive synthetic demo seeding and instructor bootstrap commands."""

import argparse, secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
from pwdlib import PasswordHash
from app.database import get_connection, init_db
from app.allocation import allocate_reviews

hashing = PasswordHash.recommended()


def bootstrap(username, password):
    init_db()
    with get_connection() as c:
        if c.execute("SELECT 1 FROM users WHERE role='instructor'").fetchone():
            raise SystemExit("An instructor already exists; refusing bootstrap.")
        instructor_id = c.execute(
            "INSERT INTO users(username,password_hash,role) VALUES(?,?,'instructor')",
            (username.lower(), hashing.hash(password)),
        ).lastrowid
        c.execute(
            "INSERT OR IGNORE INTO course_instructors(course_id,instructor_id) SELECT id,? FROM courses WHERE created_by IS NULL",
            (instructor_id,),
        )
    print(f"Instructor account created: {username}")


def seed():
    init_db()
    with get_connection() as c:
        if any(
            c.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
            for t in ("students", "users", "assignments", "submissions", "allocations")
        ):
            raise SystemExit(
                "Target database is not empty; refusing to overwrite existing data."
            )
        c.execute("BEGIN IMMEDIATE")
        course_id = c.execute(
            "SELECT id FROM courses WHERE code='DEMO' ORDER BY id LIMIT 1"
        ).fetchone()[0]
        people = [(f"demo-{i:02d}", f"Demo Student {i:02d}") for i in range(1, 11)]
        credentials = {}
        for sid, name in people:
            credentials[sid] = secrets.token_urlsafe(18)
            c.execute("INSERT INTO students(id,display_name) VALUES(?,?)", (sid, name))
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id,must_change_password) VALUES(?,?, 'student', ?,0)",
                (sid, hashing.hash(credentials[sid]), sid),
            )
            c.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, sid),
            )
        aid = c.execute(
            "INSERT INTO assignments(title,instructions,due_at,course_id) VALUES('Synthetic peer review','Demo data only; no real learner information.','2099-12-31T23:59:00Z',?)",
            (course_id,),
        ).lastrowid
        prompts = [
            "The submission demonstrates a clear understanding of the topic.",
            "Claims are supported by relevant evidence.",
            "The reasoning is coherent and well developed.",
            "The structure and writing are clear.",
            "The work offers thoughtful or original insight.",
        ]
        c.executemany(
            "INSERT INTO questions(assignment_id,prompt,question_order) VALUES(?,?,?)",
            [(aid, q, i + 1) for i, q in enumerate(prompts)],
        )
        subids = {}
        for sid, name in people:
            subids[sid] = c.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (
                    aid,
                    sid,
                    f"Sample work by {name}",
                    "This is synthetic demonstration content created for local testing only.",
                ),
            ).lastrowid
        pairs = allocate_reviews([sid for sid, _ in people], 3)
        c.executemany(
            "INSERT INTO allocations(assignment_id,reviewer_id,submission_id) VALUES(?,?,?)",
            [(aid, r, subids[s]) for r, s in pairs],
        )
        c.commit()
    print(
        "Created synthetic demo: 10 students, 1 assignment, 5 questions, 10 submissions, 30 allocations."
    )
    print(
        "One-time initial student credentials (distribute privately; not recoverable later):"
    )
    for sid, name in people:
        print(f"{sid} ({name}): {credentials[sid]}")


if __name__ == "__main__":
    seed()
