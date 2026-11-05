from pydantic import BaseModel, Field


class Login(BaseModel):
    username: str
    password: str


class StudentIn(BaseModel):
    username: str
    display_name: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class AssignmentIn(BaseModel):
    title: str
    instructions: str = ""
    due_at: str
    questions: list[dict] | None = None


class AllocationIn(BaseModel):
    reviewers_per_submission: int = 3


class ReviewDraft(BaseModel):
    answers: list[dict] = Field(default_factory=list)
    feedback: str = ""


class ModerationIn(BaseModel):
    decision: str
    note: str = ""


class FlagIn(BaseModel):
    reason: str
