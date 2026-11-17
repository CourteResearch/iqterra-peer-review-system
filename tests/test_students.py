from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook
from pwdlib import PasswordHash

from app import database
from app import email as email_module
from app.main import app
from app.routers import students as students_router


def create_instructor(username, password):
    password_hash = PasswordHash.recommended().hash(password)
    with database.get_connection() as c:
        instructor_id = c.execute(
            "INSERT INTO users(username,password_hash,role) VALUES(?,?,'instructor')",
            (username, password_hash),
        ).lastrowid
        course_id = c.execute(
            "INSERT INTO courses(title,created_by) VALUES(?,?)",
            (f"{username} course", instructor_id),
        ).lastrowid
        c.execute(
            "INSERT INTO course_instructors(course_id,instructor_id) VALUES(?,?)",
            (course_id, instructor_id),
        )
    return instructor_id, course_id


def login(client, username, password):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_bulk_add_creates_accounts_enrollments_and_one_time_credentials():
    database.init_db()
    _, course_id = create_instructor("teacher", "teacher-password-123")

    with TestClient(app) as client:
        headers = login(client, "teacher", "teacher-password-123")
        response = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json={
                "students": [
                    {"username": "jane", "display_name": "Jane Smith"},
                    {"username": "lee", "display_name": "Lee Chen"},
                ]
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["count"] == 2
    assert [student["username"] for student in body["students"]] == ["jane", "lee"]
    assert all(student["one_time_credential"] for student in body["students"])
    assert all(student["must_change_password"] for student in body["students"])
    with database.get_connection() as c:
        assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 2
        assert c.execute(
            "SELECT COUNT(*) FROM course_students WHERE course_id=?",
            (course_id,),
        ).fetchone()[0] == 2
        assert c.execute(
            "SELECT COUNT(*) FROM users WHERE role='student' AND must_change_password=1"
        ).fetchone()[0] == 2
        password_hashes = {
            row["username"]: row["password_hash"]
            for row in c.execute(
                "SELECT username,password_hash FROM users WHERE role='student'"
            )
        }
    password_hasher = PasswordHash.recommended()
    assert all(
        password_hasher.verify(
            student["one_time_credential"],
            password_hashes[student["username"]],
        )
        for student in body["students"]
    )


def test_bulk_add_prompts_before_skipping_existing_usernames():
    database.init_db()
    _, course_id = create_instructor("teacher", "teacher-password-123")

    with TestClient(app) as client:
        headers = login(client, "teacher", "teacher-password-123")
        payload = {
            "students": [
                {"username": "new-student", "display_name": "New Student"},
                {"username": "teacher", "display_name": "Duplicate"},
            ]
        }
        preview = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json=payload,
        )
        assert preview.status_code == 200
        assert preview.json()["confirmation_required"] is True
        assert preview.json()["existing_usernames"] == ["teacher"]

        with database.get_connection() as c:
            assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
            assert c.execute("SELECT COUNT(*) FROM course_students").fetchone()[0] == 0

        payload["skip_existing"] = True
        response = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json=payload,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["confirmation_required"] is False
    assert body["count"] == 1
    assert [student["username"] for student in body["students"]] == ["new-student"]
    assert body["skipped_usernames"] == ["teacher"]
    with database.get_connection() as c:
        assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1
        assert c.execute(
            "SELECT COUNT(*) FROM course_students WHERE course_id=?",
            (course_id,),
        ).fetchone()[0] == 1


def test_bulk_add_reenrolls_existing_student_removed_from_course():
    database.init_db()
    _, course_id = create_instructor("teacher", "teacher-password-123")

    with TestClient(app) as client:
        headers = login(client, "teacher", "teacher-password-123")
        initial = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json={
                "students": [
                    {"email": "jane@example.edu", "display_name": "Jane Smith"},
                ]
            },
        )
        assert initial.status_code == 201
        student = initial.json()["students"][0]

        removed = client.delete(
            f"/api/students/{student['id']}?course_id={course_id}",
            headers=headers,
        )
        assert removed.status_code == 204

        response = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json={
                "students": [
                    {"email": "JANE@example.edu", "display_name": "Jane Smith"},
                ]
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["confirmation_required"] is False
    assert body["count"] == 0
    assert body["re_enrolled_usernames"] == ["jane@example.edu"]
    assert body["students"] == []
    with database.get_connection() as c:
        assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1
        assert c.execute(
            "SELECT COUNT(*) FROM course_students WHERE course_id=?",
            (course_id,),
        ).fetchone()[0] == 1


def test_enroll_existing_reports_when_student_is_already_enrolled():
    database.init_db()
    _, course_id = create_instructor("teacher", "teacher-password-123")

    with TestClient(app) as client:
        headers = login(client, "teacher", "teacher-password-123")
        created = client.post(
            f"/api/students?course_id={course_id}",
            headers=headers,
            json={
                "email": "jane@example.edu",
                "display_name": "Jane Smith",
            },
        )
        assert created.status_code == 201
        student = created.json()

        removed = client.delete(
            f"/api/students/{student['id']}?course_id={course_id}",
            headers=headers,
        )
        assert removed.status_code == 204

        enrolled = client.post(
            f"/api/courses/{course_id}/students",
            headers=headers,
            json={"username": "jane@example.edu"},
        )
        assert enrolled.status_code == 201
        assert enrolled.json()["already_enrolled"] is False

        duplicate = client.post(
            f"/api/courses/{course_id}/students",
            headers=headers,
            json={"username": "jane@example.edu"},
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["already_enrolled"] is True


def test_bulk_add_rejects_duplicate_usernames_in_request():
    database.init_db()
    _, course_id = create_instructor("teacher", "teacher-password-123")

    with TestClient(app) as client:
        headers = login(client, "teacher", "teacher-password-123")
        response = client.post(
            f"/api/students/bulk?course_id={course_id}",
            headers=headers,
            json={
                "students": [
                    {"username": "same", "display_name": "First"},
                    {"username": "SAME", "display_name": "Second"},
                ]
            },
        )

    assert response.status_code == 422
    with database.get_connection() as c:
        assert c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0


def test_bulk_add_requires_access_to_active_course():
    database.init_db()
    create_instructor("owner", "owner-password-123")
    _, other_course_id = create_instructor("other", "other-password-123")

    with TestClient(app) as client:
        headers = login(client, "owner", "owner-password-123")
        response = client.post(
            f"/api/students/bulk?course_id={other_course_id}",
            headers=headers,
            json={"students": [{"username": "new", "display_name": "New Student"}]},
        )

    assert response.status_code == 403


def test_import_student_xlsx_returns_first_worksheet_as_csv():
    database.init_db()
    _, course_id = create_instructor("teacher-import", "teacher-password-123")
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Email", "Display Name"])
    worksheet.append(["jane@example.edu", "Jane Smith"])
    worksheet.append(["lee@example.edu", "Lee Chen"])
    spreadsheet = BytesIO()
    workbook.save(spreadsheet)

    with TestClient(app) as client:
        headers = login(client, "teacher-import", "teacher-password-123")
        response = client.post(
            f"/api/students/import-spreadsheet?course_id={course_id}",
            headers=headers,
            files={
                "file": (
                    "students.xlsx",
                    spreadsheet.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["csv_text"].splitlines() == [
        "Email,Display Name",
        "jane@example.edu,Jane Smith",
        "lee@example.edu,Lee Chen",
    ]


def test_email_student_invitation_sets_password_and_allows_email_login(monkeypatch):
    database.init_db()
    _, course_id = create_instructor("teacher-email", "teacher-password-123")
    sent = {}

    def capture_invitation(email, display_name, token):
        sent.update(email=email, display_name=display_name, token=token)

    monkeypatch.setattr(students_router, "send_student_invitation", capture_invitation)
    with TestClient(app) as client:
        headers = login(client, "teacher-email", "teacher-password-123")
        response = client.post(
            f"/api/students?course_id={course_id}",
            headers=headers,
            json={"email": "Student@Example.edu", "display_name": "Email Student"},
        )
        assert response.status_code == 201
        assert response.json()["invitation_sent"] is True
        assert response.json()["email"] == "student@example.edu"
        assert "one_time_credential" not in response.json() or response.json()["one_time_credential"] is None

        accepted = client.post(
            "/api/auth/accept-invitation",
            json={"token": sent["token"], "password": "student-password-123"},
        )
        assert accepted.status_code == 200
        student_login = client.post(
            "/api/auth/login",
            json={"username": "student@example.edu", "password": "student-password-123"},
        )

    assert sent["email"] == "student@example.edu"
    assert student_login.status_code == 200
    with database.get_connection() as c:
        assert c.execute(
            "SELECT email FROM students WHERE display_name='Email Student'"
        ).fetchone()["email"] == "student@example.edu"


def test_student_invitation_link_removes_object_object_from_base_url(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            pass

        def starttls(self, context):
            pass

        def login(self, username, password):
            pass

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setenv("IQT02_SMTP_USERNAME", "sender@example.edu")
    monkeypatch.setenv("APP", "test-only-placeholder")
    monkeypatch.setenv("IQT02_PUBLIC_URL", "http://localhost:8000[object Object]")
    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)

    email_module.send_student_invitation(
        "student@example.edu", "Email Student", "one-time-token"
    )

    assert sent_messages[0]["To"] == "student@example.edu"
    assert (
        "http://localhost:8000/?invite=one-time-token"
        in sent_messages[0].get_content()
    )
    assert "[object Object]" not in sent_messages[0].get_content()
