export type User = {
  id: number | string;
  username: string;
  display_name?: string;
  role: "instructor" | "student";
  must_change_password?: boolean;
};
export type Course = {
  id: number | string;
  title: string;
  code: string;
  term: string;
  description?: string;
  is_archived: boolean | number;
  student_count?: number;
  instructor_count?: number;
};
export type CourseGroup = {
  id: number | string;
  course_id: number | string;
  name: string;
  description?: string;
  is_archived: boolean | number;
  member_count?: number;
  members: Student[];
};
export type Question = { id?: number | string; prompt: string; order: number };
export type Template = { id?: number | string; prompt: string; title?: string };
export type Assignment = {
  id: number | string;
  title: string;
  instructions?: string;
  due_at?: string | null;
  status?: string;
  group_mode?: "course" | "within_group";
  questions?: Question[];
  my_submission?: {
    id: number | string;
    title: string;
    content?: string;
    is_submitted: boolean;
    locked: boolean;
    original_file_name?: string | null;
    file_url?: string;
  } | null;
};
export type AllocationOption = {
  id: number | null;
  student_id: string;
  student_name: string;
  group_id: number | null;
  group_name: string | null;
  is_submitted: boolean | number;
};
export type AllocationReviewer = Omit<AllocationOption, "id">;
export type Submission = {
  questions?: Question[];
  id: number | string;
  assignment_id?: number | string;
  title: string;
  content?: string;
  file_url?: string;
  created_at?: string;
};
export type Review = {
  id: number | string;
  assignment_id?: number | string;
  submission_id?: number | string;
  submission?: Submission;
  status?: string;
  due_at?: string;
  answers?: { question_id: number | string; score: number }[];
  feedback?: string;
  revision_note?: string | null;
};
export type SubmittedReview = {
  review_id: number | string;
  assignment_id: number | string;
  assignment_title: string;
  reviewer_id: string;
  reviewer_name: string;
  submission_id: number | string;
  author_id: string;
  author_name: string;
  submission_title: string;
  submission_content?: string;
  file_url?: string | null;
  feedback: string;
  submitted_at: string;
  open_flag: boolean;
  open_flag_reason?: string | null;
  questions: Question[];
  answers: { question_id: number | string; score: number }[];
};
export type OverviewData = {
  assignment?: Assignment;
  question_outcomes?: {
    question_id: number | string;
    prompt: string;
    responses: number;
    average_score: number | null;
    distribution: Record<string, number>;
  }[];
  students?: {
    id: number | string;
    display_name: string;
    allocated?: number;
    submitted?: number;
    status?: string;
  }[];
  total_students?: number;
  total_reviews?: number;
  completed_reviews?: number;
  pending_reviews?: number;
  moderation_count?: number;
};
export type ModerationItem = {
  id?: number | string;
  review_id: number | string;
  reason: string;
  submission_title: string;
  submission_content: string;
  feedback?: string;
  status?: string;
  file_url?: string;
  questions?: Question[];
  answers?: { question_id: number | string; score: number }[];
};
export type Student = { id: number | string; username: string; display_name: string };
export type StudentCreated = Student & { one_time_credential: string; must_change_password: true };
export type PasswordChangeResponse = { ok: true; user: User };
const BASE = "/api";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function getToken() {
  return sessionStorage.getItem("iqt_token");
}
export function setToken(token: string | null) {
  if (token) sessionStorage.setItem("iqt_token", token);
  else sessionStorage.removeItem("iqt_token");
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`${BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    setToken(null);
    window.dispatchEvent(new Event("iqt:unauthorized"));
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      body?.detail || body?.message || `Request failed (${response.status})`,
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export function list<T>(
  value: T[] | { items?: T[]; results?: T[] } | null | undefined,
): T[] {
  if (Array.isArray(value)) return value;
  return value?.items ?? value?.results ?? [];
}
export function messageOf(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
