"""Versioned SQLite persistence for the standalone peer-review application."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("IQT02_DATA_DIR", PROJECT_DIR / "data")).expanduser()
DATABASE_PATH = Path(
    os.getenv("IQT02_DATABASE_PATH", DATA_DIR / "iqterra.sqlite3")
).expanduser()


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=15,
        isolation_level="DEFERRED",
        factory=ClosingConnection,
    )
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=15000")
    con.execute("PRAGMA journal_mode=WAL")
    return con


@contextmanager
def transaction(connection=None, immediate=False):
    own = connection is None
    con = connection or get_connection()
    try:
        con.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        if own:
            con.close()


def init_db():
    with get_connection() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        version = con.execute(
            "SELECT COALESCE(MAX(version),0) FROM schema_migrations"
        ).fetchone()[0]
        if version < 1:
            con.executescript("""
            CREATE TABLE students(id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','instructor')), student_id TEXT UNIQUE REFERENCES students(id), is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), must_change_password INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, CHECK((role='student' AND student_id IS NOT NULL) OR (role='instructor' AND student_id IS NULL)));
            CREATE TABLE assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, instructions TEXT NOT NULL DEFAULT '', due_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')), reviewers_per_submission INTEGER NOT NULL DEFAULT 3, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE questions(id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE, prompt TEXT NOT NULL, question_order INTEGER NOT NULL, UNIQUE(assignment_id,question_order));
            CREATE TABLE submissions(id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES assignments(id), student_id TEXT NOT NULL REFERENCES students(id), title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', file_name TEXT, original_file_name TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(assignment_id,student_id));
            CREATE TABLE allocations(id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES assignments(id), reviewer_id TEXT NOT NULL REFERENCES students(id), submission_id INTEGER NOT NULL REFERENCES submissions(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(assignment_id,reviewer_id,submission_id), CHECK(reviewer_id != ''));
            CREATE TABLE reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, allocation_id INTEGER NOT NULL UNIQUE REFERENCES allocations(id), feedback TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted','reopened')), submitted_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE review_answers(review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE, question_id INTEGER NOT NULL REFERENCES questions(id), score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5), PRIMARY KEY(review_id,question_id));
            CREATE TABLE moderation_events(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id), moderator_id INTEGER NOT NULL REFERENCES users(id), decision TEXT NOT NULL CHECK(decision IN ('approved','dismissed')), note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE review_audit(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id), actor_id INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX idx_sub_assignment ON submissions(assignment_id);
            CREATE INDEX idx_alloc_assignment ON allocations(assignment_id);
            INSERT INTO schema_migrations(version) VALUES(1);
            """)
            version = 1
        if version < 2:
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status)"
            )
            con.execute("INSERT INTO schema_migrations(version) VALUES(2)")
            version = 2
        if version < 3:
            con.executescript("""
            CREATE TRIGGER allocation_no_self BEFORE INSERT ON allocations
            WHEN (SELECT student_id FROM submissions WHERE id=NEW.submission_id)=NEW.reviewer_id
            BEGIN SELECT RAISE(ABORT,'self review allocation is forbidden'); END;
            CREATE TRIGGER allocation_no_reciprocal BEFORE INSERT ON allocations
            WHEN EXISTS(SELECT 1 FROM allocations old JOIN submissions s ON s.id=old.submission_id
                        WHERE old.assignment_id=NEW.assignment_id
                        AND old.reviewer_id=(SELECT student_id FROM submissions WHERE id=NEW.submission_id)
                        AND s.student_id=NEW.reviewer_id)
            BEGIN SELECT RAISE(ABORT,'reciprocal allocation is forbidden'); END;
            INSERT INTO schema_migrations(version) VALUES(3);
            """)

        if version < 4:
            con.executescript("""
            CREATE TABLE review_flags(id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL REFERENCES reviews(id), reporter_student_id TEXT NOT NULL REFERENCES students(id), reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','approved','dismissed')), decision TEXT, moderator_id INTEGER REFERENCES users(id), moderation_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, resolved_at TEXT);
            CREATE INDEX idx_review_flags_status ON review_flags(status);
            INSERT INTO schema_migrations(version) VALUES(4);
            """)
