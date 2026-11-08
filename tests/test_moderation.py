import io
import sqlite3
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
        teacher_id = c.execute(
            "INSERT INTO users(username,password_hash,role) VALUES('teacher',?,'instructor')",
            (h.hash("teacher-password-123"),),
        ).lastrowid
        course_id = c.execute(
            "INSERT INTO courses(title,code,term,created_by) VALUES('Test course','TEST','Test term',?)",
            (teacher_id,),
        ).lastrowid
        c.execute(
            "INSERT INTO course_instructors(course_id,instructor_id) VALUES(?,?)",
            (course_id, teacher_id),
        )
        c.executemany(
            "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
            [(course_id, sid) for sid in ("s1", "s2", "s3")],
        )
        aid = c.execute(
            "INSERT INTO assignments(title,instructions,due_at,course_id) VALUES('Test assignment','','2099-01-01T00:00:00Z',?)",
            (course_id,),
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


def test_student_assignment_list_and_submission_status(setup):
    c, aid, _, submissions = setup
    ih = login(c, "teacher", "teacher-password-123")
    sh = login(c, "s1")
    other_student = login(c, "s2")

    with database.get_connection() as db:
        course_id = db.execute(
            "SELECT course_id FROM assignments WHERE id=?", (aid,)
        ).fetchone()["course_id"]
        closed_id = db.execute(
            "INSERT INTO assignments(title,due_at,status,course_id) VALUES('Closed work','2099-01-01T00:00:00Z','closed',?)",
            (course_id,),
        ).lastrowid
        unrelated_course_id = db.execute(
            "INSERT INTO courses(title,created_by) VALUES('Other course',(SELECT id FROM users WHERE username='teacher'))"
        ).lastrowid
        db.execute(
            "INSERT INTO course_instructors(course_id,instructor_id) VALUES(?,(SELECT id FROM users WHERE username='teacher'))",
            (unrelated_course_id,),
        )
        db.execute(
            "INSERT INTO assignments(title,due_at,course_id) VALUES('Private assignment','2099-01-01T00:00:00Z',?)",
            (unrelated_course_id,),
        )

    visible = c.get(
        f"/api/assignments?course_id={course_id}", headers=sh
    )
    assert visible.status_code == 200
    by_id = {item["id"]: item for item in visible.json()}
    assert aid in by_id and closed_id in by_id
    assert by_id[aid]["my_submission"]["id"] == submissions["s1"]
    assert by_id[aid]["my_submission"]["title"] == "Work s1"
    assert by_id[aid]["my_submission"]["is_submitted"] is True
    assert by_id[aid]["my_submission"]["locked"] is False
    assert c.get("/api/assignments", headers=sh).status_code == 200
    assert c.get(
        f"/api/assignments?course_id={unrelated_course_id}", headers=sh
    ).status_code == 403

    other_view = c.get(
        f"/api/assignments?course_id={course_id}", headers=other_student
    ).json()
    own = next(item for item in other_view if item["id"] == aid)["my_submission"]
    assert own["id"] == submissions["s2"]
    assert own["locked"] is True
    assert own["title"] != by_id[aid]["my_submission"]["title"]

    with database.get_connection() as db:
        new_assignment_id = db.execute(
            "INSERT INTO assignments(title,due_at,course_id) VALUES('New work','2099-01-01T00:00:00Z',?)",
            (course_id,),
        ).lastrowid
    submitted = c.post(
        f"/api/assignments/{new_assignment_id}/submissions",
        data={"title": "My new submission", "content": "My completed assessment."},
        headers=sh,
    )
    assert submitted.status_code == 200
    refreshed = c.get(
        f"/api/assignments?course_id={course_id}", headers=sh
    ).json()
    own_new = next(item for item in refreshed if item["id"] == new_assignment_id)
    assert own_new["my_submission"]["is_submitted"] is True
    assert own_new["my_submission"]["content"] == "My completed assessment."


def test_flexible_question_formats_team_forms_and_peer_reviews(setup):
    c, _, _, _ = setup
    instructor = login(c, "teacher", "teacher-password-123")
    students = {name: login(c, name) for name in ("s1", "s2", "s3")}
    with database.get_connection() as db:
        course_id = db.execute(
            "SELECT course_id FROM assignments LIMIT 1"
        ).fetchone()["course_id"]
        group_id = db.execute(
            "INSERT INTO course_groups(course_id,name) VALUES(?, 'Project team')",
            (course_id,),
        ).lastrowid
        db.executemany(
            "INSERT INTO course_group_members(course_id,group_id,student_id) VALUES(?,?,?)",
            [(course_id, group_id, student_id) for student_id in ("s1", "s2", "s3")],
        )

    questions = [
        {
            "prompt": "Rate the quality of the teammate's work.",
            "order": 1,
            "type": "rubric",
            "recipient": "peer",
            "settings": {"labels": ["Developing", "Capable", "Strong", "Excellent"]},
        },
        {
            "prompt": "What should this teammate start doing?",
            "order": 2,
            "type": "text",
            "recipient": "peer",
        },
        {
            "prompt": "How much did this teammate contribute?",
            "order": 3,
            "type": "contribution",
            "recipient": "peer",
        },
        {
            "prompt": "Distribute team contribution points.",
            "order": 4,
            "type": "points",
            "recipient": "peer",
            "settings": {"points_per_peer": 10},
        },
        {
            "prompt": "What did you learn from your team?",
            "order": 5,
            "type": "text",
            "recipient": "self",
        },
        {
            "prompt": "How well did the team work together?",
            "order": 6,
            "type": "rubric",
            "recipient": "team",
            "settings": {"labels": ["Needs work", "Adequate", "Good", "Excellent"]},
        },
    ]
    created = c.post(
        "/api/assignments",
        json={
            "title": "Flexible peer assessment",
            "course_id": course_id,
            "due_at": "2099-01-01T00:00:00Z",
            "group_mode": "within_group",
            "questions": questions,
        },
        headers=instructor,
    )
    assert created.status_code == 201, created.text
    assignment = created.json()
    assignment_id = assignment["id"]
    assert [question["type"] for question in assignment["questions"]] == [
        "rubric", "text", "contribution", "points", "text", "rubric"
    ]
    assert assignment["questions"][0]["settings"]["labels"] == [
        "Developing", "Capable", "Strong", "Excellent"
    ]

    manual = [
        {"student_id": "s1", "reviewer_ids": ["s2"]},
        {"student_id": "s2", "reviewer_ids": ["s3"]},
        {"student_id": "s3", "reviewer_ids": ["s1"]},
    ]
    allocated = c.post(
        f"/api/assignments/{assignment_id}/allocations",
        json={"mode": "manual", "reviewers_per_submission": 1, "assignments": manual},
        headers=instructor,
    )
    assert allocated.status_code == 200, allocated.text
    s1_allocation = next(
        item["id"] for item in allocated.json()["items"]
        if item["reviewer_id"] == "s1"
    )
    s1_assignment_form = c.get(
        f"/api/my/assignment-forms?course_id={course_id}&assignment_id={assignment_id}",
        headers=students["s1"],
    )
    assert s1_assignment_form.status_code == 200
    forms = {item["type"] + ":" + item["recipient"]: item
             for item in s1_assignment_form.json()["items"]}
    assert forms["points:peer"]["points_pool"] == 20
    points_question_id = forms["points:peer"]["id"]
    self_question_id = forms["text:self"]["id"]
    team_question_id = forms["rubric:team"]["id"]

    bad_points = c.put(
        f"/api/my/assignment-forms/{points_question_id}",
        json={"value": {"s2": 9, "s3": 10}},
        headers=students["s1"],
    )
    assert bad_points.status_code == 422
    good_points = c.put(
        f"/api/my/assignment-forms/{points_question_id}",
        json={"value": {"s2": 10, "s3": 10}},
        headers=students["s1"],
    )
    assert good_points.status_code == 200
    assert c.put(
        f"/api/my/assignment-forms/{self_question_id}",
        json={"value": "I learned to break down project tasks."},
        headers=students["s1"],
    ).status_code == 200
    assert c.put(
        f"/api/my/assignment-forms/{team_question_id}",
        json={"value": 3},
        headers=students["s1"],
    ).status_code == 200
    team_seen = c.get(
        f"/api/my/assignment-forms?course_id={course_id}&assignment_id={assignment_id}",
        headers=students["s2"],
    ).json()["items"]
    shared_team_answer = next(item for item in team_seen if item["id"] == team_question_id)
    assert shared_team_answer["value"] == 3
    assert shared_team_answer["submitted_at"]
    assert c.put(
        f"/api/my/assignment-forms/{team_question_id}",
        json={"value": 4},
        headers=students["s2"],
    ).status_code == 409

    submission = c.post(
        f"/api/assignments/{assignment_id}/submissions",
        data={"title": "Team member work", "content": "The project implementation and report."},
        headers=students["s3"],
    )
    assert submission.status_code == 200
    saved = c.put(
        f"/api/reviews/{s1_allocation}",
        json={
            "answers": [
                {"question_id": assignment["questions"][0]["id"], "value": 4},
                {"question_id": assignment["questions"][1]["id"], "value": "Start sharing progress earlier."},
                {"question_id": assignment["questions"][2]["id"], "value": 125},
            ],
        },
        headers=students["s1"],
    )
    assert saved.status_code == 200, saved.text
    assert c.post(
        f"/api/reviews/{s1_allocation}/submit", headers=students["s1"]
    ).status_code == 200
    detail = c.get(
        f"/api/reviews/{s1_allocation}", headers=students["s1"]
    ).json()
    values = {item["question_id"]: item["value"] for item in detail["responses"]}
    assert values[assignment["questions"][0]["id"]] == 4
    assert values[assignment["questions"][1]["id"]] == "Start sharing progress earlier."
    assert values[assignment["questions"][2]["id"]] == 125
    outcomes = c.get(
        f"/api/overview?assignment_id={assignment_id}", headers=instructor
    )
    assert outcomes.status_code == 200
    outcomes_by_id = {
        item["question_id"]: item for item in outcomes.json()["question_outcomes"]
    }
    assert outcomes_by_id[assignment["questions"][1]["id"]]["response_details"][0][
        "value"
    ] == "Start sharing progress earlier."
    assert outcomes_by_id[points_question_id]["response_details"][0]["value"] == {
        "s2": 10,
        "s3": 10,
    }
    assert outcomes_by_id[self_question_id]["response_details"][0]["value"] == (
        "I learned to break down project tasks."
    )
    assert outcomes_by_id[team_question_id]["response_details"][0]["respondent"] == (
        "Project team"
    )

    with database.get_connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM question_answers"
        ).fetchone()[0] == 3


def test_question_answer_migration_preserves_existing_ratings(setup):
    c, aid, allocation, _ = setup
    with database.get_connection() as db:
        question_id = db.execute(
            "SELECT id FROM questions WHERE assignment_id=? ORDER BY question_order LIMIT 1",
            (aid,),
        ).fetchone()["id"]
        review_id = db.execute(
            "INSERT INTO reviews(allocation_id) VALUES(?)",
            (allocation,),
        ).lastrowid
        db.execute(
            "INSERT INTO review_answers(review_id,question_id,score) VALUES(?,?,4)",
            (review_id, question_id),
        )
        db.execute("DELETE FROM schema_migrations WHERE version IN (10,11)")
        db.execute("DROP TABLE question_answers")
        db.execute("DROP TABLE assignment_form_answers")

    database.init_db()
    with database.get_connection() as db:
        migrated = db.execute(
            """
            SELECT answer_json FROM question_answers
            WHERE review_id=? AND question_id=?
            """,
            (review_id, question_id),
        ).fetchone()
    assert migrated["answer_json"] == "4"


def test_course_student_and_assignment_crud_preserve_ids_and_history(setup):
    c, aid, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course = c.get("/api/courses", headers=ih).json()["items"][0]
    course_id = course["id"]
    student_id = "s1"

    student_detail = c.get(
        f"/api/students/{student_id}?course_id={course_id}", headers=ih
    )
    assert student_detail.status_code == 200
    assert student_detail.json()["id"] == student_id
    assert student_detail.json()["course_id"] == course_id
    assert c.put(
        f"/api/students/{student_id}?course_id={course_id}",
        json={"display_name": "Updated student"},
        headers=ih,
    ).json()["display_name"] == "Updated student"
    assert c.delete(
        f"/api/students/{student_id}?course_id={course_id}", headers=ih
    ).status_code == 409

    updated_course = c.put(
        f"/api/courses/{course_id}",
        json={
            "title": "Updated course",
            "code": "UPD",
            "term": "Term 2",
            "description": "Updated details",
        },
        headers=ih,
    )
    assert updated_course.status_code == 200
    assert updated_course.json()["id"] == course_id
    assert c.get(f"/api/courses/{course_id}", headers=ih).json()["title"] == "Updated course"
    assert c.delete(f"/api/courses/{course_id}", headers=ih).status_code == 409

    updated_assignment = c.put(
        f"/api/assignments/{aid}",
        json={
            "title": "Updated assignment",
            "instructions": "Updated",
            "due_at": "2099-01-01T00:00:00Z",
            "course_id": course_id,
            "group_mode": "course",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    )
    assert updated_assignment.status_code == 200
    assert updated_assignment.json()["id"] == aid
    assert c.delete(f"/api/assignments/{aid}", headers=ih).status_code == 409


def test_empty_course_assignment_and_student_can_be_deleted(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course = c.post(
        "/api/courses",
        json={"title": "Empty CRUD course", "code": "CRUD", "term": "Test"},
        headers=ih,
    )
    assert course.status_code == 201
    course_id = course.json()["id"]

    student = c.post(
        f"/api/students?course_id={course_id}",
        json={"display_name": "Temporary student", "username": "temporary"},
        headers=ih,
    )
    assert student.status_code == 201
    student_id = student.json()["id"]
    assert c.delete(
        f"/api/students/{student_id}?course_id={course_id}", headers=ih
    ).status_code == 204

    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Empty CRUD assignment",
            "course_id": course_id,
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]
    assert c.delete(
        f"/api/assignments/{assignment_id}", headers=ih
    ).status_code == 204
    assert c.delete(f"/api/courses/{course_id}", headers=ih).status_code == 204


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


def test_instructor_can_inspect_submitted_reviews_and_request_revision(setup):
    c, aid, allocation, _ = setup
    reviewer = login(c, "s1")
    instructor = login(c, "teacher", "teacher-password-123")
    other_student = login(c, "s3")
    answers = [{"question_id": question_id, "score": 4} for question_id in range(1, 6)]
    assert c.put(
        f"/api/reviews/{allocation}",
        json={"answers": answers, "feedback": "Clear and constructive feedback."},
        headers=reviewer,
    ).status_code == 200
    assert c.post(
        f"/api/reviews/{allocation}/submit", headers=reviewer
    ).status_code == 200

    with database.get_connection() as db:
        course_id = db.execute(
            "SELECT course_id FROM assignments WHERE id=?", (aid,)
        ).fetchone()["course_id"]
        review_id = db.execute(
            "SELECT id FROM reviews WHERE allocation_id=?", (allocation,)
        ).fetchone()["id"]

    response = c.get(
        f"/api/submitted-reviews?course_id={course_id}&assignment_id={aid}",
        headers=instructor,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["review_id"] == review_id
    assert item["reviewer_name"] == "s1"
    assert item["author_name"] == "s2"
    assert item["feedback"] == "Clear and constructive feedback."
    assert len(item["questions"]) == len(item["answers"]) == 5

    assert c.get(
        f"/api/submitted-reviews?course_id={course_id}",
        headers=other_student,
    ).status_code == 403
    assert c.post(
        f"/api/reviews/{review_id}/reopen",
        json={"note": " "},
        headers=instructor,
    ).status_code == 422
    revised = c.post(
        f"/api/reviews/{review_id}/reopen",
        json={"note": "Please add a specific example to support your comments."},
        headers=instructor,
    )
    assert revised.status_code == 200
    assert revised.json()["status"] == "reopened"

    student_reviews = c.get("/api/my/reviews", headers=reviewer).json()["items"]
    assert student_reviews[0]["status"] == "reopened"
    assert student_reviews[0]["revision_note"] == (
        "Please add a specific example to support your comments."
    )
    assert c.get(
        f"/api/reviews/{allocation}", headers=reviewer
    ).json()["revision_note"] == "Please add a specific example to support your comments."

    assert c.put(
        f"/api/reviews/{allocation}",
        json={"answers": answers, "feedback": "Expanded with a useful example."},
        headers=reviewer,
    ).status_code == 200
    assert c.post(
        f"/api/reviews/{allocation}/submit", headers=reviewer
    ).status_code == 200
    updated = c.get(
        f"/api/submitted-reviews?course_id={course_id}&assignment_id={aid}",
        headers=instructor,
    ).json()["items"]
    assert len(updated) == 1
    assert updated[0]["feedback"] == "Expanded with a useful example."


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


def test_course_scoping_shared_instructors_and_archive(setup):
    c, aid, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course = c.post(
        "/api/courses",
        json={"title": "Second course", "code": "BIO101", "term": "Semester 2"},
        headers=ih,
    )
    assert course.status_code == 201
    course_id = course.json()["id"]

    payload = {
        "title": "Course-scoped assessment",
        "due_at": "2099-01-01T00:00:00Z",
        "course_id": course_id,
        "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
    }
    created = c.post("/api/assignments", json=payload, headers=ih)
    assert created.status_code == 201
    new_assignment_id = created.json()["id"]
    assert [
        item["id"]
        for item in c.get(
            f"/api/assignments?course_id={course_id}", headers=ih
        ).json()
    ] == [new_assignment_id]
    assert c.get(f"/api/assignments/{aid}", headers=ih).status_code == 200
    assert (
        c.get(
            f"/api/assignments/{new_assignment_id}",
            headers=login(c, "s2"),
        ).status_code
        == 403
    )

    with database.get_connection() as db:
        db.execute(
            "INSERT INTO users(username,password_hash,role) VALUES('other_teacher',?,'instructor')",
            (PasswordHash.recommended().hash("other-teacher-password-123"),),
        )
    other = login(c, "other_teacher", "other-teacher-password-123")
    assert c.get(f"/api/courses/{course_id}", headers=other).status_code == 403
    assert (
        c.get(
            f"/api/assignments?course_id={course_id}",
            headers=other,
        ).status_code
        == 403
    )
    assert (
        c.post(
            f"/api/courses/{course_id}/instructors",
            json={"username": "other_teacher"},
            headers=ih,
        ).status_code
        == 201
    )
    assert c.get(f"/api/courses/{course_id}", headers=other).status_code == 200
    assert (
        c.post(
            f"/api/courses/{course_id}/students",
            json={"username": "s1"},
            headers=ih,
        ).status_code
        == 201
    )
    assert [
        item["id"]
        for item in c.get(
            f"/api/students?course_id={course_id}", headers=ih
        ).json()["items"]
    ] == ["s1"]
    assert (
        c.get(
            f"/api/assignments/{new_assignment_id}",
            headers=login(c, "s1"),
        ).status_code
        == 200
    )

    assert c.post(f"/api/courses/{course_id}/archive", headers=ih).status_code == 200
    assert course_id not in [
        item["id"] for item in c.get("/api/courses", headers=ih).json()["items"]
    ]
    assert c.post(f"/api/courses/{course_id}/restore", headers=ih).status_code == 200
    assert course_id in [
        item["id"] for item in c.get("/api/courses", headers=ih).json()["items"]
    ]


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


def test_allocations_can_be_planned_before_submissions(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Plan before submission",
            "course_id": c.get("/api/courses", headers=ih).json()["items"][0]["id"],
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    ).json()
    allocated = c.post(
        f"/api/assignments/{assignment['id']}/allocations",
        json={"mode": "automatic", "reviewers_per_submission": 1},
        headers=ih,
    )
    assert allocated.status_code == 200
    assert len(allocated.json()["items"]) == 3
    details = c.get(
        f"/api/allocations?assignment_id={assignment['id']}", headers=ih
    ).json()
    assert len(details["submissions"]) == 3
    assert all(not submission["is_submitted"] for submission in details["submissions"])

    reviewer_headers = login(c, "s2")
    waiting = c.get("/api/my/reviews", headers=reviewer_headers).json()["items"]
    assert len(waiting) == 1
    assert waiting[0]["status"] == "waiting_submission"
    assert waiting[0]["submission_ready"] is False
    assert waiting[0]["submission"]["title"] == "Peer submission pending"
    submitted = c.post(
        f"/api/assignments/{assignment['id']}/submissions",
        data={"title": "Student one work", "content": "Submitted after allocation"},
        headers=login(c, "s1"),
    )
    assert submitted.status_code == 200
    available = c.get("/api/my/reviews", headers=reviewer_headers).json()["items"]
    assert len(available) == 1
    assert available[0]["submission"]["title"] == "Student one work"


def test_manual_course_allocation_and_reviewer_constraints(setup):
    c, aid, _, submissions = setup
    ih = login(c, "teacher", "teacher-password-123")
    with database.get_connection() as db:
        db.execute("DELETE FROM allocations WHERE assignment_id=?", (aid,))

    manual = [
        {"submission_id": submissions["s1"], "reviewer_ids": ["s3"]},
        {"submission_id": submissions["s2"], "reviewer_ids": ["s1"]},
        {"submission_id": submissions["s3"], "reviewer_ids": ["s2"]},
    ]
    response = c.post(
        f"/api/assignments/{aid}/allocations",
        json={"mode": "manual", "reviewers_per_submission": 1, "assignments": manual},
        headers=ih,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3
    options = c.get(f"/api/allocations?assignment_id={aid}", headers=ih).json()
    assert len(options["submissions"]) == 3
    assert {row["student_id"] for row in options["submissions"]} == set(submissions)

    with database.get_connection() as db:
        db.execute("DELETE FROM allocations WHERE assignment_id=?", (aid,))
    self_review = [dict(item) for item in manual]
    self_review[0] = {
        "submission_id": submissions["s1"],
        "reviewer_ids": ["s1"],
    }
    assert c.post(
        f"/api/assignments/{aid}/allocations",
        json={"mode": "manual", "reviewers_per_submission": 1, "assignments": self_review},
        headers=ih,
    ).status_code == 422
    reciprocal = [
        {"submission_id": submissions["s1"], "reviewer_ids": ["s2"]},
        {"submission_id": submissions["s2"], "reviewer_ids": ["s1"]},
        {"submission_id": submissions["s3"], "reviewer_ids": ["s1"]},
    ]
    response = c.post(
        f"/api/assignments/{aid}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 1,
            "assignments": reciprocal,
        },
        headers=ih,
    )
    assert response.status_code == 422
    assert "Reciprocal" in response.json()["detail"]


def test_manual_two_student_allocation_allows_only_possible_reciprocal(setup):
    c, aid, _, submissions = setup
    ih = login(c, "teacher", "teacher-password-123")
    with database.get_connection() as db:
        db.execute("DELETE FROM allocations WHERE assignment_id=?", (aid,))
        db.execute(
            "DELETE FROM submissions WHERE assignment_id=? AND student_id='s3'",
            (aid,),
        )
        db.execute(
            "DELETE FROM course_students WHERE student_id='s3' AND course_id=(SELECT course_id FROM assignments WHERE id=?)",
            (aid,),
        )
    response = c.post(
        f"/api/assignments/{aid}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 1,
            "assignments": [
                {"submission_id": submissions["s1"], "reviewer_ids": ["s2"]},
                {"submission_id": submissions["s2"], "reviewer_ids": ["s1"]},
            ],
        },
        headers=ih,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    with database.get_connection() as db:
        db.execute("DELETE FROM allocations WHERE assignment_id=?", (aid,))
    response = c.post(
        f"/api/assignments/{aid}/allocations",
        json={"mode": "automatic", "reviewers_per_submission": 1},
        headers=ih,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_manual_within_group_allocation_keeps_reviews_inside_each_team(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course_id = c.get("/api/courses", headers=ih).json()["items"][0]["id"]
    with database.get_connection() as db:
        for sid in ("s4", "s5", "s6"):
            db.execute("INSERT INTO students(id,display_name) VALUES(?,?)", (sid, sid))
            db.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, sid),
            )
    for group_name, members in (
        ("Team Alpha", ("s1", "s2", "s3")),
        ("Team Beta", ("s4", "s5", "s6")),
    ):
        group = c.post(
            f"/api/courses/{course_id}/groups",
            json={"name": group_name},
            headers=ih,
        ).json()
        for sid in members:
            assert c.post(
                f"/api/groups/{group['id']}/members",
                json={"student_id": sid},
                headers=ih,
            ).status_code == 201
    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Manual team review",
            "course_id": course_id,
            "group_mode": "within_group",
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    ).json()
    with database.get_connection() as db:
        submission_ids = {
            sid: db.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (assignment["id"], sid, f"Submission {sid}", "Work"),
            ).lastrowid
            for sid in ("s1", "s2", "s3", "s4", "s5", "s6")
        }

    assignments = [
        {"submission_id": submission_ids[target], "reviewer_ids": [reviewer]}
        for team in (("s1", "s2", "s3"), ("s4", "s5", "s6"))
        for target, reviewer in zip(team, team[1:] + team[:1])
    ]
    cross_team = [dict(item) for item in assignments]
    cross_team[0] = {
        "submission_id": submission_ids["s1"],
        "reviewer_ids": ["s4"],
    }
    response = c.post(
        f"/api/assignments/{assignment['id']}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 1,
            "assignments": cross_team,
        },
        headers=ih,
    )
    assert response.status_code == 422
    response = c.post(
        f"/api/assignments/{assignment['id']}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 1,
            "assignments": assignments,
        },
        headers=ih,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 6


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
            db.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] >= 6
        )


def test_course_migration_preserves_existing_assignments_and_roster(
    monkeypatch, tmp_path
):
    legacy_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(legacy_path) as db:
        db.executescript("""
            CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY);
            INSERT INTO schema_migrations(version) VALUES(4);
            CREATE TABLE users(id INTEGER PRIMARY KEY, role TEXT NOT NULL);
            CREATE TABLE students(id TEXT PRIMARY KEY);
            CREATE TABLE assignments(
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                instructions TEXT NOT NULL DEFAULT '',
                due_at TEXT NOT NULL
            );
            INSERT INTO users(id,role) VALUES(1,'instructor');
            INSERT INTO users(id,role) VALUES(2,'student');
            INSERT INTO students(id) VALUES('legacy-student');
            INSERT INTO assignments(id,title,due_at) VALUES(41,'Preserved activity','2099-01-01T00:00:00Z');
        """)

    monkeypatch.setattr(database, "DATABASE_PATH", legacy_path)
    database.init_db()
    with database.get_connection() as db:
        assignment = db.execute(
            "SELECT course_id FROM assignments WHERE id=41"
        ).fetchone()
        assert assignment["course_id"] is not None
        assert db.execute(
            "SELECT 1 FROM course_students WHERE student_id='legacy-student'"
        ).fetchone()
        assert db.execute(
            "SELECT 1 FROM course_instructors WHERE instructor_id=1"
        ).fetchone()


def test_group_management_and_within_group_allocation(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course_id = c.get("/api/courses", headers=ih).json()["items"][0]["id"]
    group = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Team Alpha", "description": "First team"},
        headers=ih,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    for student_id in ("s1", "s2", "s3"):
        response = c.post(
            f"/api/groups/{group_id}/members",
            json={"student_id": student_id},
            headers=ih,
        )
        assert response.status_code == 201
    with database.get_connection() as db:
        db.executemany(
            "INSERT INTO students(id,display_name) VALUES(?,?)",
            [(sid, sid) for sid in ("s4", "s5", "s6")],
        )
        db.executemany(
            "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
            [(course_id, sid) for sid in ("s4", "s5", "s6")],
        )
    second_group = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Team Beta"},
        headers=ih,
    )
    assert second_group.status_code == 201
    for student_id in ("s4", "s5", "s6"):
        assert c.post(
            f"/api/groups/{second_group.json()['id']}/members",
            json={"student_id": student_id},
            headers=ih,
        ).status_code == 201

    groups = c.get(
        f"/api/groups?course_id={course_id}", headers=ih
    ).json()["items"]
    assert groups[0]["member_count"] == 3
    assert {member["id"] for member in groups[0]["members"]} == {"s1", "s2", "s3"}
    assert groups[1]["member_count"] == 3

    archive_group = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Temporary group"},
        headers=ih,
    )
    archive_group_id = archive_group.json()["id"]
    assert c.post(
        f"/api/groups/{archive_group_id}/archive", headers=ih
    ).status_code == 200
    assert c.post(
        f"/api/groups/{archive_group_id}/restore", headers=ih
    ).status_code == 200

    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Within team review",
            "course_id": course_id,
            "group_mode": "within_group",
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]
    with database.get_connection() as db:
        submission_ids = {}
        for student_id in ("s1", "s2", "s3", "s4", "s5", "s6"):
            submission_ids[student_id] = db.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (assignment_id, student_id, f"Submission {student_id}", "Work"),
            ).lastrowid

    allocated = c.post(
        f"/api/assignments/{assignment_id}/allocations",
        json={"reviewers_per_submission": 1},
        headers=ih,
    )
    assert allocated.status_code == 200
    pairs = allocated.json()["items"]
    assert len(pairs) == 6
    group_by_student = {
        student_id: "alpha" if student_id in {"s1", "s2", "s3"} else "beta"
        for student_id in ("s1", "s2", "s3", "s4", "s5", "s6")
    }
    for pair in pairs:
        submission_owner = next(
            sid for sid, submission_id in submission_ids.items()
            if submission_id == pair["submission_id"]
        )
        assert pair["reviewer_id"] != submission_owner
        assert group_by_student[pair["reviewer_id"]] == group_by_student[submission_owner]

    assignment_payload = {
        "title": "Within team review",
        "course_id": course_id,
        "group_mode": "course",
        "due_at": "2099-01-01T00:00:00Z",
        "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
    }
    assert c.put(
        f"/api/assignments/{assignment_id}",
        json=assignment_payload,
        headers=ih,
    ).status_code == 409
    locked = c.delete(
        f"/api/groups/{group_id}/members/s1",
        headers=ih,
    )
    assert locked.status_code == 409
    assert c.post(f"/api/groups/{group_id}/archive", headers=ih).status_code == 409


def test_within_group_uses_all_teammates_as_reviewers(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course_id = c.get("/api/courses", headers=ih).json()["items"][0]["id"]
    with database.get_connection() as db:
        for sid in ("s4", "s5"):
            db.execute("INSERT INTO students(id,display_name) VALUES(?,?)", (sid, sid))
            db.execute(
                "INSERT INTO course_students(course_id,student_id) VALUES(?,?)",
                (course_id, sid),
            )
    team = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Review team"},
        headers=ih,
    ).json()
    for sid in ("s1", "s2", "s3"):
        assert c.post(
            f"/api/groups/{team['id']}/members",
            json={"student_id": sid},
            headers=ih,
        ).status_code == 201
    other_team = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Other team"},
        headers=ih,
    ).json()
    for sid in ("s4", "s5"):
        assert c.post(
            f"/api/groups/{other_team['id']}/members",
            json={"student_id": sid},
            headers=ih,
        ).status_code == 201
    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Teammate review",
            "course_id": course_id,
            "group_mode": "within_group",
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    ).json()
    with database.get_connection() as db:
        submission_ids = {
            sid: db.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (assignment["id"], sid, f"Submission {sid}", "Work"),
            ).lastrowid
            for sid in ("s1", "s2")
        }

    details = c.get(
        f"/api/allocations?assignment_id={assignment['id']}", headers=ih
    ).json()
    assert {person["student_id"] for person in details["reviewers"]} >= {
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
    }
    assert {submission["student_id"] for submission in details["submissions"]} == {
        "s1", "s2", "s3", "s4", "s5"
    }

    response = c.post(
        f"/api/assignments/{assignment['id']}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 1,
            "assignments": [
                {"student_id": "s1", "reviewer_ids": ["s2"]},
                {"student_id": "s2", "reviewer_ids": ["s3"]},
                {"student_id": "s3", "reviewer_ids": ["s1"]},
                {"student_id": "s4", "reviewer_ids": ["s5"]},
                {"student_id": "s5", "reviewer_ids": ["s4"]},
            ],
        },
        headers=ih,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 5


def test_three_person_team_can_assign_every_teammate_to_review(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course_id = c.get("/api/courses", headers=ih).json()["items"][0]["id"]
    team = c.post(
        f"/api/courses/{course_id}/groups",
        json={"name": "Three-person review team"},
        headers=ih,
    ).json()
    for student_id in ("s1", "s2", "s3"):
        assert c.post(
            f"/api/groups/{team['id']}/members",
            json={"student_id": student_id},
            headers=ih,
        ).status_code == 201

    def create_team_assignment(title):
        response = c.post(
            "/api/assignments",
            json={
                "title": title,
                "course_id": course_id,
                "group_mode": "within_group",
                "due_at": "2099-01-01T00:00:00Z",
                "questions": [{"prompt": "Assess the work."}],
            },
            headers=ih,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    automatic_assignment = create_team_assignment("Automatic teammate review")
    automatic = c.post(
        f"/api/assignments/{automatic_assignment}/allocations",
        json={"mode": "automatic", "reviewers_per_submission": 2},
        headers=ih,
    )
    assert automatic.status_code == 200, automatic.text
    automatic_pairs = {
        (
            item["reviewer_id"],
            item["submission_id"],
        )
        for item in automatic.json()["items"]
    }
    assert len(automatic_pairs) == 6
    with database.get_connection() as db:
        owner_by_submission = {
            row["id"]: row["student_id"]
            for row in db.execute(
                "SELECT id,student_id FROM submissions WHERE assignment_id=?",
                (automatic_assignment,),
            )
        }
    assert all(
        reviewer != owner_by_submission[submission_id]
        for reviewer, submission_id in automatic_pairs
    )
    for student_id in ("s1", "s2", "s3"):
        own_submission = next(
            submission_id for submission_id, owner in owner_by_submission.items()
            if owner == student_id
        )
        assert {
            reviewer for reviewer, target in automatic_pairs if target == own_submission
        } == {"s1", "s2", "s3"} - {student_id}

    manual_assignment = create_team_assignment("Manual teammate review")
    manual = c.post(
        f"/api/assignments/{manual_assignment}/allocations",
        json={
            "mode": "manual",
            "reviewers_per_submission": 2,
            "assignments": [
                {"student_id": "s1", "reviewer_ids": ["s2", "s3"]},
                {"student_id": "s2", "reviewer_ids": ["s1", "s3"]},
                {"student_id": "s3", "reviewer_ids": ["s1", "s2"]},
            ],
        },
        headers=ih,
    )
    assert manual.status_code == 200, manual.text
    assert len(manual.json()["items"]) == 6


def test_within_group_allocation_requires_group_memberships(setup):
    c, _, _, _ = setup
    ih = login(c, "teacher", "teacher-password-123")
    course_id = c.get("/api/courses", headers=ih).json()["items"][0]["id"]
    assignment = c.post(
        "/api/assignments",
        json={
            "title": "Missing groups",
            "course_id": course_id,
            "group_mode": "within_group",
            "due_at": "2099-01-01T00:00:00Z",
            "questions": [{"prompt": f"Question {i}", "order": i} for i in range(1, 6)],
        },
        headers=ih,
    ).json()
    with database.get_connection() as db:
        for student_id in ("s1", "s2", "s3"):
            db.execute(
                "INSERT INTO submissions(assignment_id,student_id,title,content) VALUES(?,?,?,?)",
                (assignment["id"], student_id, f"Submission {student_id}", "Work"),
            )
    response = c.post(
        f"/api/assignments/{assignment['id']}/allocations",
        json={"reviewers_per_submission": 1},
        headers=ih,
    )
    assert response.status_code == 422
    assert "Create active groups" in response.json()["detail"]
