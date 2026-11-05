from pydantic import BaseModel, Field
from typing import Literal


class Login(BaseModel):
    username: str
    password: str


class StudentIn(BaseModel):
    username: str
    display_name: str


class CourseIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    code: str = Field(default="", max_length=40)
    term: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=2000)


class StudentUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)


class CourseInstructorIn(BaseModel):
    username: str


class CourseStudentIn(BaseModel):
    username: str


class CourseGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class GroupMemberIn(BaseModel):
    student_id: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class AssignmentIn(BaseModel):
    title: str
    instructions: str = ""
    due_at: str
    course_id: int | None = None
    group_mode: Literal["course", "within_group"] = "course"
    questions: list[dict] | None = None


class ManualAllocationIn(BaseModel):
    submission_id: int | None = Field(default=None, gt=0)
    student_id: str | None = None
    reviewer_ids: list[str] = Field(min_length=1)


class AllocationIn(BaseModel):
    mode: Literal["automatic", "manual"] = "automatic"
    reviewers_per_submission: int = Field(default=3, ge=1)
    assignments: list[ManualAllocationIn] = Field(default_factory=list)


class ReviewDraft(BaseModel):
    answers: list[dict] = Field(default_factory=list)
    feedback: str = ""


class ModerationIn(BaseModel):
    decision: str
    note: str = ""


class RevisionRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class FlagIn(BaseModel):
    reason: str
