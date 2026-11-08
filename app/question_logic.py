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
        settings = {"labels": [label.strip()[:80] for label in labels]}
    elif question_type == "points":
        if recipient != "peer":
            raise HTTPException(
                422, f"Question {index + 1}: point distribution must be peer-focused"
            )
        points_per_peer = settings.get("points_per_peer", 10)
        if (
            isinstance(points_per_peer, bool)
            or not isinstance(points_per_peer, int)
            or points_per_peer < 1
            or points_per_peer > 100
        ):
            raise HTTPException(
                422, f"Question {index + 1} points per teammate must be from 1 to 100"
            )
        settings = {"points_per_peer": points_per_peer}
    elif question_type == "contribution":
        settings = {"minimum": 0, "equal_share": 100, "maximum": 200}
    else:
        settings = {"max_length": 4000}
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
