import os
from datetime import datetime, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app import database

JWT_SECRET = os.getenv("IQT02_JWT_SECRET")
if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("IQT02_JWT_SECRET must be set to at least 32 characters")
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)


def user_payload(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "display_name": (
            row["display_name"] if "display_name" in row.keys() else row["username"]
        ),
        "student_id": row["student_id"],
        "must_change_password": bool(row["must_change_password"]),
    }


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        data = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        with database.get_connection() as c:
            row = c.execute(
                "SELECT u.*,s.display_name FROM users u LEFT JOIN students s ON s.id=u.student_id WHERE u.id=?",
                (data.get("sub"),),
            ).fetchone()
        if not row or not row["is_active"]:
            raise ValueError()
        return row
    except Exception:
        raise HTTPException(401, "Invalid or expired session")


def role(name):
    def guard(user=Depends(current_user)):
        if user["role"] != name:
            raise HTTPException(403, "Insufficient role")
        return user

    return guard


instructor = role("instructor")
student = role("student")


def due_passed(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) < datetime.now(
            timezone.utc
        )
    except Exception:
        return False
