import io
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from app import database
from app.main import app


@pytest.fixture
def setup():
    database.init_db()
    h = PasswordHash.recommended()
    with database.get_connection() as c:
        for sid in ("s1", "s2", "s3"):
            c.execute("INSERT INTO students(id,display_name) VALUES(?,?)", (sid, sid))
            c.execute(
                "INSERT INTO users(username,password_hash,role,student_id) VALUES(?,?,'student',?)",
                (sid, h.hash("student-password-123"), sid),
            )
        c.execute(
            "INSERT INTO users(username,password_hash,role) VALUES('teacher',?,'instructor')",
            (h.hash("teacher-password-123"),),
        )
        aid = c.execute(
            "INSERT INTO assignments(title,instructions,due_at) VALUES('Test assignment','','2099-01-01T00:00:00Z')"
        ).lastrowid
        c.executemany(
            "INSERT INTO questions(assignment_id,prompt,question_order) VALUES(?,?,?)",
            [(aid, f"Question {i}", i) for i in range(1, 6)],
        )
        subs = {}
        for sid in ("s1", "s2", "s3"):
            subs[sid] = c.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (aid, sid, f"Work {sid}", "Content"),
            ).lastrowid
        alloc = c.execute(
            "INSERT INTO allocations(assignment_id,reviewer_id,submission_id) VALUES(?,?,?)",
            (aid, "s1", subs["s2"]),
        ).lastrowid
    with TestClient(app) as client:
        yield client, aid, alloc, subs


def login(c, name, pw="student-password-123"):
    response = c.post("/api/auth/login", json={"username": name, "password": pw})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_frontend_contracts_and_student_ownership(setup):
    c, aid, allocation, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    sh = login(c, "s1")
    assert "items" in c.get("/api/students", headers=ih).json()
    assert "items" in c.get("/api/my/reviews", headers=sh).json()
    assignment = c.get("/api/assignments", headers=ih).json()[0]
    assert (
        len(assignment["questions"]) == 5
        and {"id", "prompt", "order"} <= assignment["questions"][0].keys()
    )
    direct = c.get(f"/api/assignments/{aid}", headers=ih).json()
    assert (
        len(direct["questions"]) == 5
        and direct["questions"][0]["id"] == assignment["questions"][0]["id"]
    )
    assert c.get("/api/my/reviews", headers=sh).json()["items"][0]["title"] == "Work s2"
    assert (
        c.get("/api/my/reviews", headers=sh).json()["items"][0]["submission"]["title"]
        == "Work s2"
    )
    assert c.get("/api/students", headers=sh).status_code == 403


def test_draft_submit_via_allocation_and_no_duplicate_or_foreign_review(setup):
    c, _, allocation, _ = setup
    sh, other = login(c, "s1"), login(c, "s2")
    answers = [{"question_id": i, "score": 4} for i in range(1, 6)]
    assert (
        c.put(
            f"/api/reviews/{allocation}",
            json={"answers": answers, "feedback": "Thoughtful constructive feedback."},
            headers=sh,
        ).status_code
        == 200
    )
    detail = c.get(f"/api/reviews/{allocation}", headers=sh).json()
    assert len(detail["submission"]["questions"]) == 5
    assert detail["submission"]["title"] == "Work s2"
    assert c.post(f"/api/reviews/{allocation}/submit", headers=sh).status_code == 200
    assert c.post(f"/api/reviews/{allocation}/submit", headers=sh).status_code == 409
    assert (
        c.put(
            f"/api/reviews/{allocation}",
            json={"answers": answers, "feedback": "Other"},
            headers=other,
        ).status_code
        == 403
    )
    with database.get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1


def test_flags_are_private_and_moderation_queue_resolves(setup):
    c, aid, allocation, _ = setup
    sh, ih = login(c, "s1"), login(c, "teacher", "teacher-password-123")
    c.put(
        f"/api/reviews/{allocation}",
        json={
            "answers": [{"question_id": i, "score": 3} for i in range(1, 6)],
            "feedback": "Constructive detailed review.",
        },
        headers=sh,
    )
    assert (
        c.post(
            f"/api/reviews/{allocation}/flag",
            json={"reason": "Please check this review"},
            headers=sh,
        ).status_code
        == 201
    )
    assert (
        c.post(
            f"/api/reviews/{allocation}/flag", json={"reason": "Duplicate"}, headers=sh
        ).status_code
        == 409
    )
    queue = c.get(f"/api/moderation?assignment_id={aid}", headers=ih).json()
    assert len(queue["items"]) == 1 and "reporter_student_id" not in queue["items"][0]
    student_items = c.get("/api/my/reviews", headers=sh).json()["items"]
    assert all("reason" not in item for item in student_items)
    rid = queue["items"][0]["review_id"]
    assert (
        c.post(
            f"/api/reviews/{rid}/moderation",
            json={"decision": "approved", "note": "Checked"},
            headers=ih,
        ).status_code
        == 200
    )
    assert (
        c.get(f"/api/moderation?assignment_id={aid}", headers=ih).json()["items"] == []
    )


def test_file_access_and_submission_lock(setup):
    c, aid, _, subs = setup
    sh, author, unrelated, ih = (
        login(c, "s1"),
        login(c, "s2"),
        login(c, "s3"),
        login(c, "teacher", "teacher-password-123"),
    )
    response = c.post(
        f"/api/assignments/{aid}/submissions",
        data={"title": "Work s1", "content": "text"},
        files={"file": ("sample.txt", b"hello", "text/plain")},
        headers=sh,
    )
    # Existing fixture already has the author's submission, but not an allocation; this is editable.
    assert response.status_code == 200
    # Reviewer s1 can access the allocated submission for s2; unrelated s3 cannot.
    path = database.DATA_DIR / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    filename = "safe.txt"
    (path / filename).write_bytes(b"file")
    with database.get_connection() as db:
        db.execute(
            "UPDATE submissions SET file_name=?,original_file_name='original.txt' WHERE id=?",
            (filename, subs["s2"]),
        )
    assert c.get(f'/api/submissions/{subs["s2"]}/file', headers=sh).status_code == 200
    assert (
        c.get(f'/api/submissions/{subs["s2"]}/file', headers=unrelated).status_code
        == 403
    )
    assert (
        c.get(f'/api/submissions/{subs["s2"]}/file', headers=author).status_code == 200
    )
    assert c.get(f'/api/submissions/{subs["s2"]}/file', headers=ih).status_code == 200
    # Once allocated, the original author's work cannot be changed.
    assert (
        c.post(
            f"/api/assignments/{aid}/submissions",
            data={"title": "changed", "content": "changed"},
            headers=author,
        ).status_code
        == 409
    )


def test_assignment_edits_and_review_lock(setup):
    c, aid, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    payload = {
        "title": "edited",
        "instructions": "edit",
        "due_at": "2099-01-01T00:00:00Z",
        "questions": [{"prompt": f"Changed {i}", "order": i} for i in range(1, 6)],
    }
    assert c.put(f"/api/assignments/{aid}", json=payload, headers=ih).status_code == 200
    # Allocation alone does not block question edits, as no review exists.
    with database.get_connection() as db:
        db.execute("DELETE FROM allocations")
        db.execute(
            "INSERT INTO allocations(assignment_id,reviewer_id,submission_id) VALUES(?,?,?)",
            (aid, "s1", 2),
        )
    assert c.put(f"/api/assignments/{aid}", json=payload, headers=ih).status_code == 200
    with database.get_connection() as db:
        allocation_id = db.execute("SELECT id FROM allocations LIMIT 1").fetchone()[0]
        review_id = db.execute(
            "INSERT INTO reviews(allocation_id) VALUES(?)", (allocation_id,)
        ).lastrowid
    # A blank draft created by a GET does not lock the rubric.
    assert c.put(f"/api/assignments/{aid}", json=payload, headers=ih).status_code == 200
    with database.get_connection() as db:
        question_id = db.execute(
            "SELECT id FROM questions WHERE assignment_id=? LIMIT 1", (aid,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO review_answers(review_id,question_id,score) VALUES(?,?,?)",
            (review_id, question_id, 4),
        )
    assert c.put(f"/api/assignments/{aid}", json=payload, headers=ih).status_code == 409


def test_overview_question_outcomes_use_only_submitted_reviews(setup):
    c, aid, allocation, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    empty = c.get(f"/api/overview?assignment_id={aid}", headers=ih).json()[
        "question_outcomes"
    ]
    assert len(empty) == 5
    assert empty[0]["responses"] == 0
    assert empty[0]["average_score"] is None
    assert empty[0]["distribution"] == {str(score): 0 for score in range(1, 6)}
    sh = login(c, "s1")
    answers = [{"question_id": score, "score": score} for score in range(1, 6)]
    c.put(
        f"/api/reviews/{allocation}",
        json={"answers": answers, "feedback": "Helpful detailed review."},
        headers=sh,
    )
    assert (
        c.get(f"/api/overview?assignment_id={aid}", headers=ih).json()[
            "question_outcomes"
        ][0]["responses"]
        == 0
    )
    c.post(f"/api/reviews/{allocation}/submit", headers=sh)
    outcomes = c.get(f"/api/overview?assignment_id={aid}", headers=ih).json()[
        "question_outcomes"
    ]
    assert outcomes[0]["responses"] == 1
    assert outcomes[0]["average_score"] == 1.0
    assert outcomes[0]["distribution"]["1"] == 1


def test_reallocation_is_non_destructive(setup):
    c, aid, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    result = c.post(
        f"/api/assignments/{aid}/allocations",
        json={"reviewers_per_submission": 1},
        headers=ih,
    )
    assert result.status_code == 409


def test_seed_demo_temporary_database(setup, monkeypatch, capsys, tmp_path):
    import app.seed_demo as seed_demo

    monkeypatch.setattr(seed_demo, "init_db", database.init_db)
    seed_path = tmp_path / "seed.sqlite3"
    monkeypatch.setattr(database, "DATABASE_PATH", seed_path)
    monkeypatch.setattr(database, "DATA_DIR", tmp_path / "seeddata")
    seed_demo.seed()
    output = capsys.readouterr().out
    assert "10 students" in output and "demo-01" in output
    with database.get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 10
        assert db.execute("SELECT COUNT(*) FROM allocations").fetchone()[0] == 30
        assert (
            db.execute(
                "SELECT COUNT(*) FROM users WHERE must_change_password=1"
            ).fetchone()[0]
            == 0
        )
    assert len([line for line in output.splitlines() if line.startswith("demo-")]) == 10


def test_backup_and_migration(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    response = c.get("/api/exports/backup", headers=ih)
    assert response.status_code == 200 and response.content[:2] == b"PK"
    with database.get_connection() as db:
        assert (
            db.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] >= 4
        )
