"""Small shared database response helpers."""

import json


DEFAULT_RUBRIC_LABELS = [
    "Strongly disagree",
    "Disagree",
    "Neither agree nor disagree",
    "Agree",
    "Strongly agree",
]


def questions(c, aid):
    items = []
    for row in c.execute(
        "SELECT * FROM questions WHERE assignment_id=? ORDER BY question_order",
        (aid,),
    ):
        settings = json.loads(row["settings"])
        if row["question_type"] == "rubric":
            settings.setdefault("labels", DEFAULT_RUBRIC_LABELS)
            settings.setdefault("criteria", [])
            settings.setdefault("details", "")
            settings.setdefault("visibility", "instructor_only")
        if row["question_type"] == "points":
            settings.setdefault("details", "")
        if row["question_type"] == "text":
            settings.setdefault("details", "")
            settings.setdefault(
                "visibility",
                "team_named" if row["recipient"] == "self" else "instructor_only",
            )
        items.append(
            {
                "id": row["id"],
                "prompt": row["prompt"],
                "order": row["question_order"],
                "type": row["question_type"],
                "recipient": row["recipient"],
                "settings": settings,
            }
        )
    return items
