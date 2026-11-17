"""Validation helpers shared by rubric setup and student response routes."""

import json

from fastapi import HTTPException

from app.helpers import DEFAULT_RUBRIC_LABELS


QUESTION_TYPES = {"rubric", "text", "contribution", "points"}
RECIPIENTS = {"peer", "self", "team"}


def normalize_question(question, index):
    item = question.model_dump() if hasattr(question, "model_dump") else dict(question)
    prompt = item["prompt"].strip()
    if not prompt:
        raise HTTPException(422, f"Question {index + 1} cannot be blank")
    question_type = item.get("type", "rubric")
    recipient = item.get("recipient", "peer")
    settings = dict(item.get("settings") or {})
    if question_type not in QUESTION_TYPES:
        raise HTTPException(422, f"Question {index + 1} has an unsupported format")
    if recipient not in RECIPIENTS:
        raise HTTPException(422, f"Question {index + 1} has an unsupported recipient")
    if question_type == "rubric":
        labels = settings.get("labels", DEFAULT_RUBRIC_LABELS)
        if (
            not isinstance(labels, list)
            or len(labels) not in (4, 5)
            or any(not isinstance(label, str) or not label.strip() for label in labels)
            or len({label.strip().casefold() for label in labels}) != len(labels)
        ):
            raise HTTPException(
                422, f"Question {index + 1} needs four or five unique scale labels"
            )
        labels = [label.strip()[:80] for label in labels]
        criteria = settings.get("criteria", [])
        if not isinstance(criteria, list) or len(criteria) > 20:
            raise HTTPException(422, f"Question {index + 1} can have up to 20 rubric criteria")
        normalized_criteria = []
        seen_ids = set()
        for criterion_index, criterion in enumerate(criteria):
            if not isinstance(criterion, dict):
                raise HTTPException(422, f"Question {index + 1} has an invalid rubric criterion")
            name = criterion.get("name")
            criterion_id = criterion.get("id") or f"criterion_{criterion_index + 1}"
            descriptions = criterion.get("descriptions", [""] * len(labels))
            if (
                not isinstance(name, str)
                or not name.strip()
                or len(name.strip()) > 160
                or not isinstance(criterion_id, str)
                or not criterion_id
                or len(criterion_id) > 80
                or criterion_id in seen_ids
                or not isinstance(descriptions, list)
                or len(descriptions) != len(labels)
                or any(not isinstance(text, str) or len(text) > 1000 for text in descriptions)
            ):
                raise HTTPException(422, f"Question {index + 1} has an invalid rubric criterion")
            seen_ids.add(criterion_id)
            normalized_criteria.append(
                {
                    "id": criterion_id,
                    "name": name.strip(),
                    "descriptions": [text.strip() for text in descriptions],
                }
            )
        details = settings.get("details", "")
        if not isinstance(details, str) or len(details) > 4000:
            raise HTTPException(422, f"Question {index + 1} details are too long")
        visibility = settings.get("visibility", "instructor_only")
        if visibility not in {"instructor_only", "team_named", "recipient_anonymous"}:
            raise HTTPException(422, f"Question {index + 1} has an invalid response visibility")
        settings = {
            "labels": labels,
            "criteria": normalized_criteria,
            "details": details.strip(),
            "visibility": visibility,
        }
    elif question_type == "points":
        if recipient != "peer":
            raise HTTPException(
                422, f"Question {index + 1}: point distribution must be peer-focused"
            )
        details = settings.get("details", "")
        if not isinstance(details, str) or len(details) > 4000:
            raise HTTPException(422, f"Question {index + 1} details are too long")
        points_pool = settings.get("points_pool", 100)
        if points_pool != 100 or isinstance(points_pool, bool):
            raise HTTPException(422, f"Question {index + 1} must use a fixed 100-point pool")
        if settings.get("include_self", True) is not True:
            raise HTTPException(422, f"Question {index + 1} must include the responding student")
        settings = {
            "points_pool": 100,
            "include_self": True,
            "details": details.strip(),
        }
    elif question_type == "contribution":
        details = settings.get("details", "")
        if not isinstance(details, str) or len(details) > 4000:
            raise HTTPException(422, f"Question {index + 1} details are too long")
        settings = {
            "minimum": 0,
            "equal_share": 100,
            "maximum": 200,
            "details": details.strip(),
        }
    else:
        details = settings.get("details", "")
        if not isinstance(details, str) or len(details) > 4000:
            raise HTTPException(422, f"Question {index + 1} details are too long")
        visibility = settings.get(
            "visibility",
            "team_named" if recipient == "self" else "instructor_only",
        )
        if visibility not in {"instructor_only", "team_named", "recipient_anonymous"}:
            raise HTTPException(422, f"Question {index + 1} has an invalid response visibility")
        settings = {
            "max_length": 4000,
            "details": details.strip(),
            "visibility": visibility,
        }
    return {
        "prompt": prompt,
        "order": index + 1,
        "type": question_type,
        "recipient": recipient,
        "settings": settings,
    }


def validate_answer(question, value):
    question_type = question["question_type"]
    settings = json.loads(question["settings"])
    if question_type == "rubric":
        labels = settings.get("labels", DEFAULT_RUBRIC_LABELS)
        criteria = settings.get("criteria", [])
        if criteria:
            if (
                not isinstance(value, dict)
                or set(value) != {criterion["id"] for criterion in criteria}
                or any(
                    isinstance(value[criterion["id"]], bool)
                    or not isinstance(value[criterion["id"]], int)
                    or not 1 <= value[criterion["id"]] <= len(labels)
                    for criterion in criteria
                )
            ):
                raise HTTPException(422, "Rate every rubric criterion using one of its performance levels")
            return value
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= len(labels)
        ):
            raise HTTPException(
                422, f"Choose a rating from 1 to {len(labels)} for this question"
            )
        return value
    if question_type == "text":
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(422, "A written response is required")
        if len(value) > settings.get("max_length", 4000):
            raise HTTPException(422, "Written response is too long")
        return value.strip()
    if question_type == "contribution":
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 200:
            raise HTTPException(422, "Contribution scores must be from 0 to 200")
        return value
    raise HTTPException(422, "Point distributions must be submitted in the team form")
