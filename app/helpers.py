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
        if row["question_type"] == "rubric" and not settings.get("labels"):
            settings["labels"] = DEFAULT_RUBRIC_LABELS
        if row["question_type"] == "points":
            settings.setdefault("points_per_peer", 10)
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
