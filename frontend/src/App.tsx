import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  api,
  AllocationOption,
  AllocationReviewer,
  Assignment,
  Course,
  CourseGroup,
  getToken,
  list,
  ModerationItem,
  OverviewData,
  Question,
  Review,
  setToken,
  Submission,
  SubmittedReview,
  Template,
  User,
  messageOf,
} from "./api";

type Action = <T>(
  action: () => Promise<T>,
  then?: (value: T) => void,
) => Promise<T | undefined>;
type Screen =
  | "overview"
  | "courses"
  | "groups"
  | "assignments"
  | "roster"
  | "allocation"
  | "moderation"
  | "submitted_reviews"
  | "reviews"
  | "submit";
const SCALE = [
  "Strongly disagree",
  "Disagree",
  "Neither agree nor disagree",
  "Agree",
  "Strongly agree",
];
function Button({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="button" {...props}>
      {children}
    </button>
  );
}
function Notice({
  kind = "info",
  children,
}: {
  kind?: "info" | "error" | "success";
  children: React.ReactNode;
}) {
  return (
    <div
      className={`notice ${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [screen, setScreen] = useState<Screen>("overview");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [assignmentId, setAssignmentId] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const signedOut = useCallback(() => {
    setUser(null);
    setToken(null);
  }, []);
  useEffect(() => {
    const fn = () => signedOut();
    window.addEventListener("iqt:unauthorized", fn);
    return () => window.removeEventListener("iqt:unauthorized", fn);
  }, [signedOut]);
  useEffect(() => {
    if (!getToken()) return;
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => signedOut());
  }, [signedOut]);
  useEffect(() => {
    if (!user) return;
    api<{ items: Course[] }>("/courses")
      .then(({ items }) => {
        setCourses(items);
        setSelectedCourseId((current) =>
          items.some((course) => String(course.id) === current)
            ? current
            : String(items[0]?.id || ""),
        );
      })
      .catch((e) => setError(messageOf(e)));
  }, [user]);
  useEffect(() => {
    if (user) setScreen(user.role === "student" ? "submit" : "overview");
  }, [user]);
  const run = useCallback(
    async <T,>(action: () => Promise<T>, then?: (value: T) => void) => {
      setBusy(true);
      setError("");
      setSuccess("");
      try {
        const result = await action();
        then?.(result);
        return result;
      } catch (e) {
        setError(messageOf(e));
        return undefined;
      } finally {
        setBusy(false);
      }
    },
    [],
  );
  if (!user) return <Login onLogin={(u) => setUser(u)} />;
  if (user.must_change_password) return <PasswordChange user={user} onChanged={setUser} onSignOut={signedOut} />;
  const instructor = user.role === "instructor";
  const selectedCourse = courses.find(
    (course) => String(course.id) === selectedCourseId,
  );
  const courseAvailable = Boolean(selectedCourse && !selectedCourse.is_archived);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">i</span>
          <span>
            <b>iqterra</b>
            <small>peer review</small>
          </span>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <div className="course-switch">
          <label>
            <span>Current course</span>
            <select
              aria-label="Select course"
              value={selectedCourseId}
              onChange={(e) => {
                setSelectedCourseId(e.target.value);
                setAssignmentId("");
              }}
            >
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
          </label>
          {selectedCourse && (
            <small>
              {[selectedCourse.code, selectedCourse.term]
                .filter(Boolean)
                .join(" · ") || "Course workspace"}
            </small>
          )}
        </div>
        <nav className="main-nav" aria-label="Workspace navigation">
          {(instructor
            ? [
              ["courses", "Courses"],
              ["groups", "Groups"],
              ["overview", "Overview"],
                ["assignments", "Assignments"],
                ["roster", "Student roster"],
                ["allocation", "Allocation"],
                ["submitted_reviews", "Submitted reviews"],
                ["moderation", "Moderation"],
              ]
            : [
                ["submit", "My assignments"],
                ["reviews", "Reviews to complete"],
              ]
          ).map(([id, label]) => (
            <button
              key={id}
              className={`nav-item ${screen === id ? "active" : ""}`}
              onClick={() => {
                setScreen(id as Screen);
                setError("");
                setSuccess("");
              }}
            >
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p className="muted">
            Moodle integration
            <br />
            <b>Not configured</b>
          </p>
          <button className="logout" onClick={signedOut}>
            Sign out · {user.display_name || user.username}
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <span>
            {instructor ? "Instructor workspace" : "Student workspace"}
          </span>
          <span className="sandbox-pill">Local peer review</span>
        </header>
        <div className="content-wrap">
          <div className="page-heading">
            <div>
              <div className="eyebrow">IQTERRA · PEER ASSESSMENT</div>
              <h1>{heading(screen, instructor)}</h1>
              <p>
                {instructor
                  ? "Manage assignments and review progress from live workspace data."
                  : "Review allocated peer work and submit your own work."}
              </p>
            </div>
            {instructor && (
              <div className="heading-actions">
                <Button
                  onClick={() => {
                    setScreen("assignments");
                    setError("");
                  }}
                >
                  New assignment
                </Button>
                <Backup onError={setError} />
              </div>
            )}
          </div>
          {error && <Notice kind="error">{error}</Notice>}
          {success && <Notice kind="success">{success}</Notice>}
          {busy && <Notice>Loading or saving…</Notice>}
          {instructor && screen === "courses" ? (
            <Courses
              run={run}
              courses={courses}
              onCourses={setCourses}
              onSuccess={setSuccess}
              onSelect={(id) => {
                setSelectedCourseId(id);
                setScreen("overview");
                setAssignmentId("");
              }}
            />
          ) : instructor && screen === "groups" && selectedCourse ? (
            <Groups
              run={run}
              courseId={selectedCourseId}
              onSuccess={setSuccess}
            />
          ) : !selectedCourse ? (
            <section className="panel">
              <Empty>
                {instructor
                  ? "Create a course to start organizing your teaching."
                  : "You are not enrolled in a course yet. Ask your lecturer to add you."}
              </Empty>
            </section>
          ) : instructor && !courseAvailable ? (
            <section className="panel">
              <Notice>This course is archived and read-only.</Notice>
              <Courses
                run={run}
                courses={courses}
                onCourses={setCourses}
                onSuccess={setSuccess}
                onSelect={(id) => {
                  setSelectedCourseId(id);
                  setScreen("overview");
                  setAssignmentId("");
                }}
              />
            </section>
          ) : instructor ? (
            screen === "overview" ? (
              <Overview
                run={run}
                courseId={selectedCourseId}
                assignmentId={assignmentId}
                onAssignment={setAssignmentId}
                onNavigate={setScreen}
              />
            ) : screen === "assignments" ? (
              <Assignments run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
            ) : screen === "roster" ? (
              <Roster run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
            ) : screen === "allocation" ? (
              <Allocation run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
            ) : screen === "submitted_reviews" ? (
              <SubmittedReviews
                run={run}
                courseId={selectedCourseId}
                onSuccess={setSuccess}
              />
            ) : (
              <Moderation run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
            )
          ) : screen === "submit" ? (
            <SubmissionForm run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
          ) : (
            <MyReviews run={run} courseId={selectedCourseId} onSuccess={setSuccess} />
          )}
        </div>
        <footer className="main-footer">
          <span>IQTerra Peer Review · Moodle integration not configured</span>
          <span>External integrations are disabled</span>
        </footer>
      </main>
    </div>
  );
}
function heading(screen: Screen, instructor: boolean) {
  return instructor
    ? (
        {
          overview: "Instructor overview",
          courses: "Courses",
          groups: "Course groups",
          assignments: "Assignments",
          roster: "Student roster",
          allocation: "Review allocation",
          submitted_reviews: "Submitted reviews",
          moderation: "Moderation",
        } as Record<string, string>
      )[screen]
    : screen === "submit"
      ? "My assignments"
      : "Your peer reviews";
}
function PasswordChange({ user, onChanged, onSignOut }: { user: User; onChanged: (u: User) => void; onSignOut: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setError("");
    if (next.length < 12) { setError("Choose a password with at least 12 characters."); return; }
    if (next !== confirm) { setError("The new passwords do not match."); return; }
    setBusy(true);
    try {
      const result = await api<{ok:true;user:User}>("/auth/password", {method:"POST", body:JSON.stringify({current_password:current,new_password:next})});
      onChanged(result.user);
    } catch (err) { setError(messageOf(err)); } finally { setBusy(false); }
  }
  return <main className="login-shell"><form className="login-card" onSubmit={submit}>
    <div className="brand"><span className="brand-mark">i</span><span><b>iqterra</b><small>peer review</small></span></div>
    <h1>Set a new password</h1><p>For your account security, change the one-time password before continuing.</p>
    {error && <Notice kind="error">{error}</Notice>}
    <label>Current password<input type="password" autoComplete="current-password" required value={current} onChange={e=>setCurrent(e.target.value)}/></label>
    <label>New password<input type="password" autoComplete="new-password" minLength={12} required value={next} onChange={e=>setNext(e.target.value)}/></label>
    <p className="muted">Use at least 12 characters. The server validates password requirements.</p>
    <label>Confirm new password<input type="password" autoComplete="new-password" required value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>
    <Button disabled={busy}>{busy ? "Updating…" : "Change password"}</Button><button type="button" className="logout" onClick={onSignOut}>Sign out</button>
  </form></main>;
}
function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{
        token: string;
        access_token?: string;
        user: User;
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(result.token || result.access_token || null);
      if (!(result.token || result.access_token))
        throw new Error("The login response did not include a session token.");
      onLogin(result.user);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-shell">
      <form className="login-card" onSubmit={submit}>
        <div className="brand">
          <span className="brand-mark">i</span>
          <span>
            <b>iqterra</b>
            <small>peer review</small>
          </span>
        </div>
        <h1>Welcome back</h1>
        <p>Sign in to your peer-review workspace.</p>
        {error && <Notice kind="error">{error}</Notice>}
        <label>
          Username
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <Button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
      </form>
    </main>
  );
}
function useAssignments(
  run: <T>(a: () => Promise<T>, cb?: (v: T) => void) => Promise<T | undefined>,
  courseId: string,
) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const refresh = useCallback(
    () =>
      run<Assignment[] | { items?: Assignment[]; results?: Assignment[] }>(
        () => api(`/assignments?course_id=${encodeURIComponent(courseId)}`),
        (v) => setAssignments(list(v)),
      ),
    [courseId, run],
  );
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { assignments, refresh };
}
function Overview({
  run,
  courseId,
  assignmentId,
  onAssignment,
  onNavigate,
}: {
  run: Action;
  courseId: string;
  assignmentId: string;
  onAssignment: (v: string) => void;
  onNavigate: (v: Screen) => void;
}) {
  const { assignments } = useAssignments(run, courseId);
  const active = assignmentId || String(assignments[0]?.id || "");
  useEffect(() => {
    if (!assignmentId && assignments[0])
      onAssignment(String(assignments[0].id));
  }, [assignmentId, assignments, onAssignment]);
  const [data, setData] = useState<OverviewData | null>(null);
  useEffect(() => {
    if (!active) return;
    void run<OverviewData>(
      () => api(`/overview?assignment_id=${encodeURIComponent(active)}`),
      setData,
    );
  }, [active, run]);
  const completed = data?.completed_reviews;
  const total = data?.total_reviews;
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Review progress</h2>
        <select
          value={active}
          onChange={(e) => onAssignment(e.target.value)}
          aria-label="Select assignment"
        >
          <option value="">Select an assignment</option>
          {assignments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </div>
      {!assignments.length ? (
        <Empty>No assignments yet. Create an assignment to get started.</Empty>
      ) : (
        data && (
          <>
            <div className="metric-grid">
              <Metric label="Students" value={data.total_students} />
              <Metric label="Reviews completed" value={completed} />
              <Metric label="Total reviews" value={total} />
              <Metric
                label="Awaiting moderation"
                value={data.moderation_count}
              />
            </div>
            <div className="progress-line">
              <span
                style={{
                  width: total
                    ? `${Math.min(100, ((completed || 0) / total) * 100)}%`
                    : "0%",
                }}
              />
            </div>
            <p className="muted">
              {completed ?? "—"} of {total ?? "—"} reviews completed
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Allocated</th>
                    <th>Submitted</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.students || []).map((s) => (
                    <tr key={s.id}>
                      <td>{s.display_name}</td>
                      <td>{s.allocated ?? "—"}</td>
                      <td>{s.submitted ?? "—"}</td>
                      <td>
                        <span className="status-pill">
                          {s.status || "In progress"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data.students?.length && (
                <Empty>
                  No progress rows were returned for this assignment.
                </Empty>
              )}
            </div>
            <h3>Question-level results</h3>
            <p className="muted">
              Results include submitted reviews only; response counts exclude
              drafts.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Responses</th>
                    <th>Average</th>
                    {[1, 2, 3, 4, 5].map((score) => (
                      <th key={score}>{score}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data.question_outcomes || []).map((outcome) => (
                    <tr key={outcome.question_id}>
                      <td>{outcome.prompt}</td>
                      <td>{outcome.responses}</td>
                      <td>
                        {outcome.average_score == null
                          ? "—"
                          : outcome.average_score.toFixed(2)}
                      </td>
                      {[1, 2, 3, 4, 5].map((score) => (
                        <td key={score}>
                          {outcome.distribution?.[String(score)] ?? 0}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data.question_outcomes?.length && (
                <Empty>No question-level results are available yet.</Empty>
              )}
            </div>
            <div className="action-row">
              <Button onClick={() => onNavigate("allocation")}>
                Manage allocation
              </Button>
              <Button onClick={() => onNavigate("moderation")}>
                Open moderation
              </Button>
            </div>
          </>
        )
      )}
    </section>
  );
}
function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "—"}</div>
    </div>
  );
}
function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
function Courses({
  run,
  courses,
  onCourses,
  onSelect,
  onSuccess,
}: {
  run: Action;
  courses: Course[];
  onCourses: (courses: Course[]) => void;
  onSelect: (id: string) => void;
  onSuccess: (message: string) => void;
}) {
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [title, setTitle] = useState("");
  const [code, setCode] = useState("");
  const [term, setTerm] = useState("");
  const [description, setDescription] = useState("");
  const [instructorUsername, setInstructorUsername] = useState("");
  const [activeCourseId, setActiveCourseId] = useState("");
  const [editingCourseId, setEditingCourseId] = useState<string | null>(null);

  const refresh = useCallback(
    () =>
      run<{ items: Course[] }>(
        () => api("/courses?include_archived=true"),
        ({ items }) => setAllCourses(items),
      ),
    [run],
  );
  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function create(e: FormEvent) {
    e.preventDefault();
    const course = await run<Course>(() =>
      api(editingCourseId ? `/courses/${editingCourseId}` : "/courses", {
        method: editingCourseId ? "PUT" : "POST",
        body: JSON.stringify({ title, code, term, description }),
      }),
    );
    if (!course) return;
    setTitle("");
    setCode("");
    setTerm("");
    setDescription("");
    setEditingCourseId(null);
    await refresh();
    onCourses(editingCourseId
      ? courses.map((item) => String(item.id) === editingCourseId ? { ...item, ...course } : item)
      : [...courses, course]);
    if (!editingCourseId) onSelect(String(course.id));
    onSuccess(editingCourseId ? "Course updated." : "Course created.");
  }

  function editCourse(course: Course) {
    setEditingCourseId(String(course.id));
    setTitle(course.title);
    setCode(course.code);
    setTerm(course.term);
    setDescription(course.description || "");
  }

  async function deleteCourse(course: Course) {
    if (!window.confirm(`Permanently delete empty course "${course.title}"?`)) return;
    await run(
      () => api(`/courses/${course.id}`, { method: "DELETE" }),
      () => {
        void refresh();
        onCourses(courses.filter((item) => String(item.id) !== String(course.id)));
        onSuccess("Course deleted.");
      },
    );
  }

  async function archive(course: Course) {
    if (!window.confirm(`Archive "${course.title}"? Course records will be preserved.`))
      return;
    const result = await run(() =>
      api(`/courses/${course.id}/archive`, { method: "POST" }),
    );
    if (result === undefined) return;
    await refresh();
    const active = courses.filter((item) => String(item.id) !== String(course.id));
    onCourses(active);
    if (active.length) onSelect(String(active[0].id));
  }

  async function restore(course: Course) {
    const result = await run(() =>
      api(`/courses/${course.id}/restore`, { method: "POST" }),
    );
    if (result === undefined) return;
    await refresh();
    onCourses([...courses, { ...course, is_archived: false }]);
  }

  async function addInstructor(e: FormEvent) {
    e.preventDefault();
    if (!activeCourseId) return;
    const result = await run(() =>
      api(`/courses/${activeCourseId}/instructors`, {
        method: "POST",
        body: JSON.stringify({ username: instructorUsername }),
      }),
    );
    if (result !== undefined) setInstructorUsername("");
  }

  return (
    <>
      <section className="panel">
        <h2>{editingCourseId ? "Edit course" : "Create a course"}</h2>
        <form className="stack" onSubmit={create}>
          <label>
            Course name
            <input required value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <div className="form-grid">
            <label>
              Course code
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. 805A" />
            </label>
            <label>
              Teaching period
              <input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="e.g. Semester 1, 2026" />
            </label>
          </div>
          <label>
            Description
            <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <div className="action-row">
            <Button>{editingCourseId ? "Save course" : "Create course"}</Button>
            {editingCourseId && (
              <Button className="secondary" type="button" onClick={() => {
                setEditingCourseId(null);
                setTitle("");
                setCode("");
                setTerm("");
                setDescription("");
              }}>Cancel</Button>
            )}
          </div>
        </form>
      </section>
      <section className="panel">
        <h2>Your courses</h2>
        {allCourses.length ? allCourses.map((course) => (
          <div className="list-row" key={course.id}>
            <div>
              <b>{course.title}</b>
              <small>
                ID: {course.id} ·{" "}
                {[course.code, course.term, `${course.student_count ?? 0} students`]
                  .filter(Boolean).join(" · ")}
                {course.is_archived ? " · Archived" : ""}
              </small>
            </div>
            <div className="action-row">
              {!course.is_archived && (
                <>
                  <Button className="secondary" onClick={() => onSelect(String(course.id))}>Open course</Button>
                  <Button className="secondary" onClick={() => editCourse(course)}>Edit</Button>
                  <Button className="secondary" onClick={() => setActiveCourseId(String(course.id))}>Manage instructors</Button>
                  <Button className="secondary" onClick={() => void archive(course)}>Archive</Button>
                  <Button className="secondary" onClick={() => void deleteCourse(course)}>Delete if empty</Button>
                </>
              )}
              {course.is_archived && (
                <Button className="secondary" onClick={() => void restore(course)}>Restore</Button>
              )}
            </div>
          </div>
        )) : <Empty>No courses yet. Create one to get started.</Empty>}
      </section>
      {activeCourseId && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Share course access</h2>
            <button className="logout" onClick={() => setActiveCourseId("")}>Close</button>
          </div>
          <p className="muted">Add an existing instructor account as a co-instructor for this course.</p>
          <form className="form-grid" onSubmit={addInstructor}>
            <label>
              Instructor username
              <input required value={instructorUsername} onChange={(e) => setInstructorUsername(e.target.value)} />
            </label>
            <Button>Add co-instructor</Button>
          </form>
        </section>
      )}
    </>
  );
}
function Groups({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (message: string) => void;
}) {
  const [groups, setGroups] = useState<CourseGroup[]>([]);
  const [students, setStudents] = useState<import("./api").Student[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<CourseGroup | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const load = useCallback(
    () =>
      run(
        async () => {
          const [groupResult, studentResult] = await Promise.all([
            api<{ items: CourseGroup[] }>(
              `/groups?course_id=${encodeURIComponent(courseId)}&include_archived=true`,
            ),
            api<{ items?: import("./api").Student[]; students?: import("./api").Student[] }>(
              `/students?course_id=${encodeURIComponent(courseId)}`,
            ),
          ]);
          setGroups(groupResult.items);
          setStudents(list(studentResult));
        },
      ),
    [courseId, run],
  );
  useEffect(() => {
    void load();
  }, [load]);

  const assignedIds = new Set(
    groups.flatMap((group) => group.members.map((member) => String(member.id))),
  );
  const availableStudents = students.filter(
    (student) => !assignedIds.has(String(student.id)),
  );

  async function create(e: FormEvent) {
    e.preventDefault();
    const result = await run(() =>
      api(`/courses/${courseId}/groups`, {
        method: "POST",
        body: JSON.stringify({ name, description }),
      }),
    );
    if (result === undefined) return;
    setName("");
    setDescription("");
    onSuccess("Group created.");
    void load();
  }

  async function assign(groupId: string) {
    const studentId = selections[groupId];
    if (!studentId) return;
    const result = await run(() =>
      api(`/groups/${groupId}/members`, {
        method: "POST",
        body: JSON.stringify({ student_id: studentId }),
      }),
    );
    if (result !== undefined) {
      setSelections((current) => ({ ...current, [groupId]: "" }));
      onSuccess("Student assigned to group.");
      void load();
    }
  }

  async function removeMember(group: CourseGroup, student: import("./api").Student) {
    const result = await run(() =>
      api(`/groups/${group.id}/members/${encodeURIComponent(String(student.id))}`, {
        method: "DELETE",
      }),
    );
    if (result !== undefined) {
      onSuccess(`${student.display_name} moved to unassigned students.`);
      void load();
    }
  }

  async function saveGroup(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const result = await run(() =>
      api(`/groups/${editing.id}`, {
        method: "PUT",
        body: JSON.stringify({ name: editName, description: editDescription }),
      }),
    );
    if (result !== undefined) {
      setEditing(null);
      onSuccess("Group details updated.");
      void load();
    }
  }

  async function archive(group: CourseGroup) {
    if (!window.confirm(`Archive "${group.name}"? Membership and review history will be preserved.`))
      return;
    const result = await run(() =>
      api(`/groups/${group.id}/archive`, { method: "POST" }),
    );
    if (result !== undefined) {
      onSuccess("Group archived.");
      void load();
    }
  }

  async function restore(group: CourseGroup) {
    const result = await run(() =>
      api(`/groups/${group.id}/restore`, { method: "POST" }),
    );
    if (result !== undefined) {
      onSuccess("Group restored.");
      void load();
    }
  }

  return (
    <>
      <section className="panel">
        <h2>Create a group</h2>
        <p className="muted">
          Organize enrolled students into teams. Each student can be in one group per course.
        </p>
        <form className="stack" onSubmit={create}>
          <label>
            Group name
            <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Team Alpha" />
          </label>
          <label>
            Description (optional)
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <Button>Create group</Button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Course groups</h2>
          <span className="status-pill">{groups.filter((group) => !group.is_archived).length} active</span>
        </div>
        {groups.length ? groups.map((group) => (
          <section className="group-card" key={group.id}>
            <div className="panel-heading">
              <div>
                <h3>{group.name}</h3>
                {group.description && <p className="muted">{group.description}</p>}
                <small className="muted">{group.members.length} members{group.is_archived ? " · Archived" : ""}</small>
              </div>
              <div className="action-row">
                {!group.is_archived && (
                  <>
                    <Button className="secondary" onClick={() => {
                      setEditing(group);
                      setEditName(group.name);
                      setEditDescription(group.description || "");
                    }}>Edit</Button>
                    <Button className="secondary" onClick={() => void archive(group)}>Archive</Button>
                  </>
                )}
                {group.is_archived && <Button className="secondary" onClick={() => void restore(group)}>Restore</Button>}
              </div>
            </div>
            {group.members.length ? (
              <ul className="group-members">
                {group.members.map((member) => (
                  <li key={member.id}>
                    <span><b>{member.display_name}</b><small>{member.username}</small></span>
                    <Button className="secondary" onClick={() => void removeMember(group, member)}>Unassign</Button>
                  </li>
                ))}
              </ul>
            ) : <Empty>No students are assigned to this group yet.</Empty>}
            {!group.is_archived && (
              <div className="group-assign-row">
                <label>
                  Add or move a student
                  <select
                    value={selections[String(group.id)] || ""}
                    onChange={(e) => setSelections((current) => ({ ...current, [String(group.id)]: e.target.value }))}
                  >
                    <option value="">Select a student to add or move</option>
                    {students
                      .filter((student) => !group.members.some((member) => String(member.id) === String(student.id)))
                      .map((student) => (
                      <option key={student.id} value={student.id}>{student.display_name} · {student.username}</option>
                    ))}
                  </select>
                </label>
                <Button disabled={!selections[String(group.id)]} onClick={() => void assign(String(group.id))}>Assign student</Button>
              </div>
            )}
          </section>
        )) : <Empty>No groups yet. Create teams above to organize this course.</Empty>}
      </section>

      <section className="panel">
        <h2>Unassigned students <span className="muted">({availableStudents.length})</span></h2>
        {availableStudents.length ? (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Student</th><th>Username</th><th>Group status</th></tr></thead>
              <tbody>{availableStudents.map((student) => (
                <tr key={student.id}><td>{student.display_name}</td><td>{student.username}</td><td>Not assigned</td></tr>
              ))}</tbody>
            </table>
          </div>
        ) : <Empty>Every enrolled student is assigned to a group.</Empty>}
      </section>

      {editing && (
        <section className="panel">
          <h2>Edit {editing.name}</h2>
          <form className="stack" onSubmit={saveGroup}>
            <label>Group name<input required value={editName} onChange={(e) => setEditName(e.target.value)} /></label>
            <label>Description<textarea rows={2} value={editDescription} onChange={(e) => setEditDescription(e.target.value)} /></label>
            <div className="action-row">
              <Button>Save changes</Button>
              <Button className="secondary" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </form>
        </section>
      )}
    </>
  );
}
function Assignments({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const { assignments, refresh } = useAssignments(run, courseId);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<Assignment | null>(null);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [due, setDue] = useState("");
  const [groupMode, setGroupMode] = useState<"course" | "within_group">("course");
  const [questions, setQuestions] = useState<Question[]>(
    Array.from({ length: 5 }, (_, i) => ({ prompt: "", order: i + 1 })),
  );
  useEffect(() => {
    void run<Template[] | { items?: Template[]; results?: Template[] }>(
      () =>
        api<Template[] | { items?: Template[]; results?: Template[] }>(
          "/question-templates",
        ),
      (v) => {
        const values = list<Template>(v);
        setTemplates(values);
        setQuestions((prev) =>
          prev.some((q) => q.prompt.trim())
            ? prev
            : Array.from({ length: 5 }, (_, i) => ({
                prompt: values[i]?.prompt || "",
                order: i + 1,
              })),
        );
      },
    );
  }, [run]);
  function start(a?: Assignment) {
    setEditing(a || null);
    setTitle(a?.title || "");
    setInstructions(a?.instructions || "");
    setDue(a?.due_at?.slice(0, 16) || "");
    setGroupMode(a?.group_mode || "course");
    setQuestions(
      Array.from({ length: 5 }, (_, i) => ({
        prompt: a?.questions?.[i]?.prompt || templates[i]?.prompt || "",
        order: i + 1,
      })),
    );
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    const payload = {
      title,
      instructions,
      due_at: due ? new Date(due).toISOString() : null,
      course_id: Number(courseId),
      group_mode: groupMode,
      questions: questions.map((q) => ({ prompt: q.prompt, order: q.order })),
    };
    const result = await run(() =>
      api(editing ? `/assignments/${editing.id}` : "/assignments", {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(payload),
      }),
    );
    if (result !== undefined) {
      onSuccess(editing ? "Draft assignment updated." : "Assignment created.");
      setEditing(null);
      void refresh();
    }
  }
  async function remove(a: Assignment) {
    if (!window.confirm(`Permanently delete "${a.title}"? Assignments with submissions or review history are protected.`))
      return;
    await run(
      () => api(`/assignments/${a.id}`, { method: "DELETE" }),
      () => {
        onSuccess("Assignment deleted.");
        void refresh();
      },
    );
  }
  return (
    <>
      <section className="panel">
        <div className="panel-heading">
          <h2>{editing ? "Edit assignment" : "Create assignment"}</h2>
          <span className="status-pill">
            Exactly five questions · 1–5 Likert
          </span>
        </div>
        <form className="stack" onSubmit={save}>
          <label>
            Assignment title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Instructions
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={3}
            />
          </label>
          <label>
            Peer review groups
            <select
              value={groupMode}
              onChange={(e) =>
                setGroupMode(e.target.value === "within_group" ? "within_group" : "course")
              }
            >
              <option value="course">Across the whole course</option>
              <option value="within_group">Only within each student group</option>
            </select>
          </label>
          {groupMode === "within_group" && (
            <p className="muted">
              Assign every enrolled student to an active group. Allocations can be planned before submissions; reviews become available when the target student submits.
            </p>
          )}
          <label>
            Due date
            <input
              required
              type="datetime-local"
              value={due}
              onChange={(e) => setDue(e.target.value)}
            />
          </label>
          <h3>Assessment questions</h3>
          {questions.map((q, i) => (
            <label key={i}>
              Question {i + 1}
              <input
                required
                value={q.prompt}
                onChange={(e) =>
                  setQuestions((prev) =>
                    prev.map((x, j) =>
                      j === i ? { ...x, prompt: e.target.value } : x,
                    ),
                  )
                }
              />
            </label>
          ))}
          <p className="muted">
            Templates provided: {templates.length || "loading"}. Edit any of the
            five questions above.
          </p>
          <Button type="submit">
            {editing ? "Save draft" : "Create assignment"}
          </Button>
        </form>
      </section>
      <section className="panel">
        <h2>Assignments</h2>
        {assignments.length ? (
          assignments.map((a) => (
            <div className="list-row" key={a.id}>
              <div>
                <b>{a.title}</b>
                <small>
                  ID: {a.id} ·{" "}
                  {a.due_at
                    ? new Date(a.due_at).toLocaleString()
                    : "No due date"}{" "}
                  · {a.status || "Draft"}
                </small>
              </div>
              <div className="action-row">
                <Button onClick={() => start(a)}>Edit</Button>
                <Button className="secondary" onClick={() => void remove(a)}>Delete if empty</Button>
              </div>
            </div>
          ))
        ) : (
          <Empty>No assignments found.</Empty>
        )}
      </section>
    </>
  );
}
function Roster({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const [students, setStudents] = useState<import("./api").Student[]>([]);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [existingUsername, setExistingUsername] = useState("");
  const [credential, setCredential] = useState("");
  const [copied, setCopied] = useState(false);
  const [editingStudent, setEditingStudent] = useState<import("./api").Student | null>(null);
  const [editDisplayName, setEditDisplayName] = useState("");
  const load = useCallback(
    () =>
      run<any>(
        () => api(`/students?course_id=${encodeURIComponent(courseId)}`),
        (v) => setStudents(list(v)),
      ),
    [courseId, run],
  );
  useEffect(() => {
    void load();
  }, [load]);
  async function add(e: FormEvent) {
    e.preventDefault();
    const x = await run(() =>
      api<import("./api").StudentCreated>(
        `/students?course_id=${encodeURIComponent(courseId)}`,
        {
        method: "POST",
        body: JSON.stringify({ display_name: name, username }),
        },
      ),
    );
    if (x !== undefined) {
      setName("");
      setUsername("");
      setCredential(x.one_time_credential);
      setCopied(false);
      onSuccess("Student added. Share the one-time credential privately.");
      void load();
    }
  }
  async function enrollExisting(e: FormEvent) {
    e.preventDefault();
    const result = await run(() =>
      api(`/courses/${courseId}/students`, {
        method: "POST",
        body: JSON.stringify({ username: existingUsername }),
      }),
    );
    if (result !== undefined) {
      setExistingUsername("");
      onSuccess("Existing student enrolled in this course.");
      void load();
    }
  }
  async function saveStudent(e: FormEvent) {
    e.preventDefault();
    if (!editingStudent) return;
    const result = await run(() =>
      api(
        `/students/${encodeURIComponent(String(editingStudent.id))}?course_id=${encodeURIComponent(courseId)}`,
        {
          method: "PUT",
          body: JSON.stringify({ display_name: editDisplayName }),
        },
      ),
    );
    if (result !== undefined) {
      setEditingStudent(null);
      onSuccess("Student updated.");
      void load();
    }
  }
  async function removeStudent(student: import("./api").Student) {
    if (!window.confirm(`Remove ${student.display_name} from this course? Existing submissions and review history are protected.`))
      return;
    await run(
      () => api(
        `/students/${encodeURIComponent(String(student.id))}?course_id=${encodeURIComponent(courseId)}`,
        { method: "DELETE" },
      ),
      () => {
        onSuccess("Student removed from this course.");
        void load();
      },
    );
  }
  return (
    <>
      <section className="panel">
        <h2>Add student</h2>
        <form className="form-grid" onSubmit={add}>
          <label>
            Display name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Username
            <input
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <Button>Add student</Button>
        </form>
      </section>
      <section className="panel">
        <h2>Enroll an existing student</h2>
        <form className="form-grid" onSubmit={enrollExisting}>
          <label>
            Student username
            <input required value={existingUsername} onChange={(e) => setExistingUsername(e.target.value)} />
          </label>
          <Button>Enroll student</Button>
        </form>
      </section>
      {credential && <section className="credential-panel" aria-labelledby="credential-title"><div><h2 id="credential-title">One-time student credential</h2><p>Share this credential privately with the student. It is shown only once and is not stored by this page.</p><code>{credential}</code></div><div className="action-row"><Button onClick={() => { void navigator.clipboard.writeText(credential).then(() => setCopied(true)).catch(() => onSuccess("Select and copy the credential manually; clipboard access was unavailable.")); }}> {copied ? "Copied" : "Copy credential"}</Button><Button className="secondary" onClick={() => setCredential("")}>Dismiss</Button></div></section>}
      {editingStudent && (
        <section className="panel">
          <h2>Edit student · ID {editingStudent.id}</h2>
          <form className="form-grid" onSubmit={saveStudent}>
            <label>
              Display name
              <input
                required
                value={editDisplayName}
                onChange={(e) => setEditDisplayName(e.target.value)}
              />
            </label>
            <div className="action-row">
              <Button>Save student</Button>
              <Button className="secondary" type="button" onClick={() => setEditingStudent(null)}>Cancel</Button>
            </div>
          </form>
        </section>
      )}
      <section className="panel">
        <h2>
          Roster <span className="muted">({students.length})</span>
        </h2>
        {students.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{s.display_name}</td>
                    <td>{s.username}</td>
                    <td>
                      <div className="action-row">
                        <Button className="secondary" onClick={() => {
                          setEditingStudent(s);
                          setEditDisplayName(s.display_name);
                        }}>Edit</Button>
                        <Button className="secondary" onClick={() => void removeStudent(s)}>Remove</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>
            No students yet. Add students to this local demo roster; there is no
            fixed app limit.
          </Empty>
        )}
      </section>
    </>
  );
}
function Allocation({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run, courseId);
  const [assignmentId, setAssignment] = useState("");
  const [count, setCount] = useState(3);
  const [mode, setMode] = useState<"automatic" | "manual">("automatic");
  const [items, setItems] = useState<{ id: number; reviewer_id: string; submission_id: number }[]>([]);
  const [submissions, setSubmissions] = useState<AllocationOption[]>([]);
  const [reviewers, setReviewers] = useState<AllocationReviewer[]>([]);
  const [manualReviewers, setManualReviewers] = useState<Record<string, string[]>>({});
  const active = assignmentId || String(assignments[0]?.id || "");
  const selectedAssignment = assignments.find((item) => String(item.id) === active);
  useEffect(() => {
    if (active)
      void run<{
        items: typeof items;
        submissions: AllocationOption[];
        reviewers: AllocationReviewer[];
      }>(
        () => api(`/allocations?assignment_id=${encodeURIComponent(active)}`),
        (v) => {
          setItems(v.items || []);
          setSubmissions(v.submissions || []);
          setReviewers(v.reviewers || []);
          setManualReviewers({});
        },
      );
  }, [active, run]);
  const eligibleReviewers = (submission: AllocationOption) =>
    (selectedAssignment?.group_mode === "within_group" ? reviewers : submissions).filter(
      (candidate) =>
        candidate.student_id !== submission.student_id &&
        (selectedAssignment?.group_mode !== "within_group" ||
          candidate.group_id === submission.group_id),
    );
  const manualReady =
    submissions.length > 0 &&
    submissions.every(
      (submission) =>
        (manualReviewers[String(submission.student_id)] || []).length === count,
    );
  async function allocate() {
    const r = await run(() =>
      api(`/assignments/${active}/allocations`, {
        method: "POST",
        body: JSON.stringify({
          mode,
          reviewers_per_submission: count,
          ...(mode === "manual"
            ? {
                assignments: submissions.map((submission) => ({
                  student_id: submission.student_id,
                  reviewer_ids: manualReviewers[String(submission.student_id)] || [],
                })),
              }
            : {}),
        }),
      }),
    );
    if (r !== undefined) {
      onSuccess(mode === "manual" ? "Manual allocation saved." : "Automatic allocation generated.");
      const result = r as { items: typeof items };
      setItems(result.items);
      const current = await run<{
        submissions: AllocationOption[];
        reviewers: AllocationReviewer[];
      }>(() => api(`/allocations?assignment_id=${encodeURIComponent(active)}`));
      if (current) {
        setSubmissions(current.submissions);
        setReviewers(current.reviewers);
      }
    }
  }
  function toggleReviewer(targetId: string, reviewerId: string) {
    const key = targetId;
    setManualReviewers((current) => {
      const selected = current[key] || [];
      const updated = selected.includes(reviewerId)
        ? selected.filter((id) => id !== reviewerId)
        : selected.length < count
          ? [...selected, reviewerId]
          : selected;
      return { ...current, [key]: updated };
    });
  }
  const studentName = (studentId: string) =>
    reviewers.find((reviewer) => reviewer.student_id === studentId)?.student_name ||
    submissions.find((submission) => submission.student_id === studentId)?.student_name ||
    studentId;
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Allocation coverage</h2>
        <select value={active} onChange={(e) => setAssignment(e.target.value)}>
          <option value="">Select assignment</option>
          {assignments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </div>
      {!assignments.length ? (
        <Empty>Create an assignment before allocating reviews.</Empty>
      ) : (
        <>
          <div className="action-row">
            <label>
              Allocation method
              <select value={mode} onChange={(e) => setMode(e.target.value as "automatic" | "manual")}>
                <option value="automatic">Automatic (balanced)</option>
                <option value="manual">Manual</option>
              </select>
            </label>
            <label>
              Reviewers per submission{" "}
              <input
                type="number"
                min="1"
                value={count}
                onChange={(e) => {
                  setCount(Math.max(1, Number(e.target.value) || 1));
                  setManualReviewers({});
                }}
              />
            </label>
            <Button
              disabled={!active || items.length > 0 || (mode === "manual" && !manualReady)}
              onClick={allocate}
            >
              {mode === "manual" ? "Save manual allocation" : "Generate allocation"}
            </Button>
          </div>
          <p className="muted">
            {selectedAssignment?.group_mode === "within_group"
              ? "Team mode: each student reviews classmates from their own team only."
              : "Course mode: students review peers across the whole course."}
            {" "}Review loads are balanced; self-reviews and reciprocal pairs are not allowed.
          </p>
          {mode === "manual" && !items.length && submissions.length > 0 && (
            <div className="stack">
              <h3>Choose reviewers for each submission</h3>
              {submissions.map((submission) => {
                const eligible = eligibleReviewers(submission);
                const targetKey = String(submission.student_id);
                const selected = manualReviewers[targetKey] || [];
                return (
                  <fieldset key={submission.student_id} className="panel">
                    <legend>
                      {submission.student_name}'s work
                      {!submission.is_submitted && " (submission pending)"}
                      {selectedAssignment?.group_mode === "within_group" && submission.group_name
                        ? ` · ${submission.group_name}`
                        : ""}
                    </legend>
                    {eligible.length ? (
                      <div className="action-row">
                        {eligible.map((reviewer) => (
                          <label key={reviewer.student_id}>
                            <input
                              type="checkbox"
                              checked={selected.includes(reviewer.student_id)}
                              disabled={!selected.includes(reviewer.student_id) && selected.length >= count}
                              onChange={() => toggleReviewer(targetKey, reviewer.student_id)}
                            />
                            {reviewer.student_name}
                          </label>
                        ))}
                      </div>
                    ) : (
                      <p className="muted">No eligible reviewers. Check group membership and submitted work.</p>
                    )}
                    <small>{selected.length} of {count} reviewers selected</small>
                  </fieldset>
                );
              })}
            </div>
          )}
          {items.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reviewer</th>
                    <th>Submission</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((x, i) => (
                    <tr key={x.id ?? i}>
                      <td>{studentName(x.reviewer_id)}</td>
                      <td>
                        {submissions.find((submission) => submission.id === x.submission_id)?.student_name || x.submission_id}
                        {submissions.find((submission) => submission.id === x.submission_id)?.is_submitted ? "" : " (submission pending)"}
                      </td>
                      <td>
                        {submissions.find((submission) => submission.id === x.submission_id)?.is_submitted
                          ? "Allocated"
                          : "Waiting for submission"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty>No allocation records returned yet.</Empty>
          )}
        </>
      )}
    </section>
  );
}
function Moderation({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run, courseId);
  const [aid, setAid] = useState("");
  const [items, setItems] = useState<ModerationItem[]>([]);
  const active = aid || String(assignments[0]?.id || "");
  const load = useCallback(
    () =>
      active
        ? run<any>(
            () =>
              api(`/moderation?assignment_id=${encodeURIComponent(active)}`),
            (v) => setItems(list(v)),
          )
        : Promise.resolve(undefined),
    [active, run],
  );
  useEffect(() => {
    void load();
  }, [load]);
  async function decide(
    item: ModerationItem,
    decision: "approved" | "dismissed",
  ) {
    const note = window.prompt("Optional moderation note:") || "";
    const id = item.review_id || item.id;
    const r = await run(() =>
      api(`/reviews/${id}/moderation`, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
      }),
    );
    if (r !== undefined) {
      onSuccess(`Review ${decision}.`);
      void load();
    }
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Open flag queue</h2>
        <select value={active} onChange={(e) => setAid(e.target.value)}>
          <option value="">Select assignment</option>
          {assignments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </div>
      {items.length ? (
        items.map((x) => (
          <div className="moderation-card" key={x.id}>
            <b>{x.submission_title || "Review flagged for moderation"}</b>
            <p><b>Flag reason:</b> {x.reason || "No flag reason provided."}</p>
            <h3>Flagged submission</h3><div className="submission-content">{x.submission_content || "No text content was provided."}{x.file_url && <p><a href={x.file_url} target="_blank" rel="noreferrer">Open attachment</a></p>}</div>
            {x.feedback && <p><b>Reviewer feedback:</b> {x.feedback}</p>}
            {!!x.questions?.length && <div><h3>Scores</h3>{x.questions.slice(0,5).map(q => { const answer=x.answers?.find(a=>String(a.question_id)===String(q.id)); return <p key={String(q.id)}>{q.prompt}: <b>{answer ? `${answer.score} / 5` : "Not scored"}</b></p>; })}</div>}
            <small>{x.status || "Pending decision"}</small>
            <div className="action-row">
              <Button onClick={() => void decide(x, "approved")}>
                Approve
              </Button>
              <Button
                className="secondary"
                onClick={() => void decide(x, "dismissed")}
              >
                Dismiss
              </Button>
            </div>
          </div>
        ))
      ) : (
        <Empty>No open flags for this assignment.</Empty>
      )}
    </section>
  );
}
function SubmittedReviews({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run, courseId);
  const [assignmentId, setAssignmentId] = useState("");
  const [items, setItems] = useState<SubmittedReview[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [requesting, setRequesting] = useState<string | null>(null);
  const active =
    assignmentId === "all"
      ? ""
      : assignmentId || String(assignments[0]?.id || "");
  const load = useCallback(
    () =>
      run<{ items?: SubmittedReview[] }>(
        () =>
          api(
            `/submitted-reviews?course_id=${encodeURIComponent(courseId)}${
              active ? `&assignment_id=${encodeURIComponent(active)}` : ""
            }`,
          ),
        (value) => setItems(list(value)),
      ),
    [active, courseId, run],
  );
  useEffect(() => {
    void load();
  }, [load]);

  async function requestRevision(item: SubmittedReview) {
    const note = (notes[String(item.review_id)] || "").trim();
    if (!note) return;
    const result = await run(() =>
      api(`/reviews/${item.review_id}/reopen`, {
        method: "POST",
        body: JSON.stringify({ note }),
      }),
    );
    if (result !== undefined) {
      setRequesting(null);
      setNotes((current) => ({ ...current, [String(item.review_id)]: "" }));
      await load();
      onSuccess(`Revision requested from ${item.reviewer_name}.`);
    }
  }

  async function decideFlag(
    item: SubmittedReview,
    decision: "approved" | "dismissed",
  ) {
    const note = window.prompt("Optional moderation note:") || "";
    const result = await run(() =>
      api(`/reviews/${item.review_id}/moderation`, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
      }),
    );
    if (result !== undefined) {
      await load();
      onSuccess(`Flag ${decision}.`);
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Submitted peer reviews</h2>
          <p className="muted">
            Review scores and feedback submitted by students. Authors and reviewers are visible to instructors.
          </p>
        </div>
        <label>
          Assignment
          <select
            aria-label="Filter submitted reviews by assignment"
            value={assignmentId || active}
            onChange={(event) => setAssignmentId(event.target.value)}
          >
            <option value="all">All assignments</option>
            {assignments.map((assignment) => (
              <option key={assignment.id} value={assignment.id}>
                {assignment.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      {items.length ? (
        items.map((item) => {
          const reviewId = String(item.review_id);
          const isRequesting = requesting === reviewId;
          return (
            <article className="moderation-card submitted-review-card" key={reviewId}>
              <div className="panel-heading">
                <div>
                  <b>{item.assignment_title}</b>
                  <small>
                    Submitted {new Date(item.submitted_at).toLocaleString()}
                    {item.open_flag ? " · Flagged for moderation" : ""}
                  </small>
                </div>
                <span className="status-pill">Submitted</span>
              </div>
              {item.open_flag && (
                <Notice>
                  <b>Student flag:</b> {item.open_flag_reason || "No reason provided."}
                </Notice>
              )}
              <p>
                <b>Reviewer:</b> {item.reviewer_name}
                {" · "}
                <b>Work by:</b> {item.author_name}
              </p>
              <h3>{item.submission_title}</h3>
              <div className="submission-content">
                {item.submission_content || "No text content was provided."}
                {item.file_url && (
                  <p>
                    <a href={item.file_url} target="_blank" rel="noreferrer">
                      Open submitted attachment
                    </a>
                  </p>
                )}
              </div>
              <h3>Assessment scores</h3>
              {item.questions.map((question) => {
                const answer = item.answers.find(
                  (entry) => String(entry.question_id) === String(question.id),
                );
                return (
                  <p className="submitted-review-score" key={String(question.id)}>
                    {question.prompt}
                    <b>{answer ? `${answer.score} / 5 · ${SCALE[answer.score - 1]}` : "Not scored"}</b>
                  </p>
                );
              })}
              <h3>Written feedback</h3>
              <p className="review-feedback">{item.feedback}</p>
              {isRequesting ? (
                <div className="stack revision-request">
                  <label>
                    Explain what the student should revise
                    <textarea
                      rows={3}
                      required
                      maxLength={2000}
                      value={notes[reviewId] || ""}
                      onChange={(event) =>
                        setNotes((current) => ({
                          ...current,
                          [reviewId]: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <div className="action-row">
                    <Button
                      disabled={!notes[reviewId]?.trim()}
                      onClick={() => void requestRevision(item)}
                    >
                      Send revision request
                    </Button>
                    <Button
                      className="secondary"
                      onClick={() => setRequesting(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="action-row">
                  {item.open_flag && (
                    <>
                      <Button onClick={() => void decideFlag(item, "approved")}>
                        Approve flag
                      </Button>
                      <Button
                        className="secondary"
                        onClick={() => void decideFlag(item, "dismissed")}
                      >
                        Dismiss flag
                      </Button>
                    </>
                  )}
                  <Button
                    className="secondary"
                    onClick={() => setRequesting(reviewId)}
                  >
                    Request revision
                  </Button>
                </div>
              )}
            </article>
          );
        })
      ) : (
        <Empty>
          {active
            ? "No reviews have been submitted for this assignment yet."
            : "No submitted reviews in this course yet."}
        </Empty>
      )}
    </section>
  );
}
function MyReviews({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [active, setActive] = useState<Review | null>(null);
  const load = useCallback(
    () =>
      run<any>(
        () => api(`/my/reviews?course_id=${encodeURIComponent(courseId)}`),
        (v) => setReviews(list(v)),
      ),
    [courseId, run],
  );
  useEffect(() => {
    void load();
  }, [load]);
  return active ? (
    <ReviewEditor
      review={active}
      run={run}
      onBack={() => {
        setActive(null);
        void load();
      }}
      onSuccess={onSuccess}
    />
  ) : (
    <section className="panel">
      <h2>Reviews allocated to you</h2>
      {reviews.length ? (
        reviews.map((r) => (
          <div className="list-row" key={r.id}>
            <div>
              <b>{r.submission?.title || "Peer submission"}</b>
              <small>
                {r.status || "Ready to review"}
                {r.due_at
                  ? ` · Due ${new Date(r.due_at).toLocaleDateString()}`
                  : ""}
              </small>
              <p className="muted">Author identity is hidden.</p>
            </div>
            <Button
              onClick={() =>
                void run<Review>(() => api(`/reviews/${r.id}`), setActive)
              }
            >
              {r.status === "submitted" ? "View review" : "Review submission"}
            </Button>
          </div>
        ))
      ) : (
        <Empty>No peer submissions are currently allocated to you.</Empty>
      )}
    </section>
  );
}
function ReviewEditor({
  review,
  run,
  onBack,
  onSuccess,
}: {
  review: Review;
  run: Action;
  onBack: () => void;
  onSuccess: (s: string) => void;
}) {
  const [detail, setDetail] = useState<Review>(review);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState("");
  const [validation, setValidation] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);
  useEffect(() => {
    void run<Review>(
      () => api(`/reviews/${review.id}`),
      (r) => {
        setDetail(r);
        setFeedback(r.feedback || "");
        const saved: Record<string, number> = {};
        (r.answers || []).forEach(
          (a) => (saved[String(a.question_id)] = a.score),
        );
        setScores(saved);
        if (r.submission?.questions) setQuestions(r.submission.questions);
        else if (r.assignment_id)
          void run<Assignment>(
            () => api(`/assignments/${r.assignment_id}`),
            (a) => setQuestions(a.questions || []),
          );
      },
    );
  }, [review.id, run]);
  const submission = detail.submission;
  const questionsToRate = questions.slice(0, 5);
  const submitted = detail.status?.toLowerCase() === "submitted";
  async function save(submit = false) {
    if (submitted) return;
    if (
      questionsToRate.length !== 5 ||
      questionsToRate.some((q) => q.id === undefined)
    ) {
      setValidation(
        "The five questions for this assignment are not available.",
      );
      return;
    }
    const answers = questionsToRate.flatMap((q) => {
      const score = scores[String(q.id)];
      return score ? [{ question_id: q.id!, score }] : [];
    });
    if (submit && answers.length !== 5) {
      setValidation(
        "Choose a rating for each of the five questions before submitting.",
      );
      return;
    }
    setValidation("");
    const saved = await run(() =>
      api(`/reviews/${review.id}`, {
        method: "PUT",
        body: JSON.stringify({ answers, feedback }),
      }),
    );
    if (saved !== undefined && submit) {
      const done = await run(() =>
        api(`/reviews/${review.id}/submit`, { method: "POST" }),
      );
      if (done !== undefined) {
        onSuccess("Review submitted successfully.");
        onBack();
      }
    } else if (saved !== undefined) onSuccess("Draft saved.");
  }
  async function flagForInstructor() {
    const reason = window.prompt("What should the instructor review?")?.trim();
    if (!reason) return;
    const result = await run(() =>
      api(`/reviews/${review.id}/flag`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    );
    if (result !== undefined)
      onSuccess("Flag sent to the instructor for review.");
  }
  return (
    <section className="panel">
      <Button className="secondary" onClick={onBack}>
        ← Back to reviews
      </Button>
      <div className="review-heading">
        <h2>{submission?.title || "Peer submission"}</h2>
        <span className="status-pill">Anonymous author</span>
      </div>
      <div className="submission-content">
        {submission?.content ||
          "Submission content is not available in this response."}
        {submission?.file_url && (
          <p>
            <a href={submission.file_url} target="_blank" rel="noreferrer">
              Open attachment
            </a>
          </p>
        )}
      </div>
      <h3>Assessment · five statements</h3>
      {detail.revision_note && (
        <Notice>
          Your lecturer requested a revision: {detail.revision_note}
        </Notice>
      )}
      {submitted && (
        <Notice kind="success">
          This review has been submitted and is read-only.
        </Notice>
      )}
      {questionsToRate.length !== 5 ? (
        <Notice>The five assignment questions are not available yet.</Notice>
      ) : (
        questionsToRate.map((q, i) => (
          <div className="criterion" key={String(q.id ?? i)}>
            <b>{q.prompt}</b>
            <div className="likert">
              {SCALE.map((label, n) => (
                <label key={n}>
                  <input
                    type="radio"
                    name={`q-${q.id}`}
                    disabled={submitted}
                    checked={scores[String(q.id)] === n + 1}
                    onChange={() =>
                      setScores((v) => ({ ...v, [String(q.id)]: n + 1 }))
                    }
                  />
                  <span>{n + 1}</span>
                  <small>{label}</small>
                </label>
              ))}
            </div>
          </div>
        ))
      )}
      <label>
        Written feedback
        <textarea
          rows={5}
          disabled={submitted}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      </label>
      <p className="muted">
        Add at least 10 characters of written feedback to submit. You can save a
        draft before it is complete.
      </p>
      {validation && <Notice kind="error">{validation}</Notice>}
      <div className="action-row">
        <Button className="secondary" onClick={() => void flagForInstructor()}>
          Flag this work for instructor
        </Button>
      </div>
      <div className="action-row">
        <Button
          className="secondary"
          disabled={submitted || questionsToRate.length !== 5}
          onClick={() => void save(false)}
        >
          Save draft
        </Button>
        <Button
          disabled={submitted || questionsToRate.length !== 5}
          onClick={() => void save(true)}
        >
          Submit review
        </Button>
      </div>
    </section>
  );
}
function SubmissionForm({
  run,
  courseId,
  onSuccess,
}: {
  run: Action;
  courseId: string;
  onSuccess: (s: string) => void;
}) {
  const { assignments, refresh } = useAssignments(run, courseId);
  const [assignmentId, setAid] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState("");
  const activeAssignmentId = assignmentId || String(assignments[0]?.id || "");
  const selected = assignments.find(
    (assignment) => String(assignment.id) === activeAssignmentId,
  );
  const submission = selected?.my_submission;
  const pastDue = Boolean(
    selected?.due_at && new Date(selected.due_at).getTime() < Date.now(),
  );
  const canSubmit = selected?.status === "open" && !pastDue && !submission?.locked;

  useEffect(() => {
    if (!assignmentId && assignments[0])
      setAid(String(assignments[0].id));
  }, [assignmentId, assignments]);

  useEffect(() => {
    setTitle(submission?.is_submitted ? submission.title : "");
    setContent(submission?.is_submitted ? submission.content || "" : "");
    setFile(null);
    setValidation("");
  }, [activeAssignmentId, assignments]);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!selected || !canSubmit) return;
    if (!content.trim() && !file && !submission?.file_url) { setValidation("Add text or choose a file before submitting."); return; }
    setValidation("");
    const form = new FormData();
    form.set("title", title);
    form.set("content", content);
    if (file) form.set("file", file);
    const r = await run(() =>
      api(`/assignments/${activeAssignmentId}/submissions`, {
        method: "POST",
        body: form,
      }),
    );
    if (r !== undefined) {
      setTitle("");
      setContent("");
      setFile(null);
      await refresh();
      onSuccess(submission?.is_submitted ? "Submission updated." : "Submission received.");
    }
  }
  return (
    <>
    <section className="panel">
      <div className="panel-heading">
        <h2>Assignments for this course</h2>
        <span className="status-pill">{assignments.length} total</span>
      </div>
      {assignments.length ? (
        assignments.map((assignment) => {
          const ownSubmission = assignment.my_submission;
          const overdue = Boolean(
            assignment.due_at && new Date(assignment.due_at).getTime() < Date.now(),
          );
          const state = ownSubmission?.is_submitted
            ? "Submitted"
            : assignment.status !== "open"
              ? "Closed"
              : overdue
                ? "Past due"
                : "Not submitted";
          return (
          <div className="list-row student-assignment" key={assignment.id}>
            <div>
              <b>{assignment.title}</b>
              <small>
                Due {assignment.due_at
                  ? new Date(assignment.due_at).toLocaleString()
                  : "date not set"}
                {" · "}{state}
              </small>
            </div>
            <Button
              className="secondary"
              aria-pressed={activeAssignmentId === String(assignment.id)}
              onClick={() => setAid(String(assignment.id))}
            >
              {activeAssignmentId === String(assignment.id) ? "Selected" : "View"}
            </Button>
          </div>
          );
        })
      ) : (
        <Empty>No assignments are available in this course yet. Check with your lecturer if you expect to see one.</Empty>
      )}
    </section>
    {selected && (
    <section className="panel">
      <div className="panel-heading">
        <h2>{selected.title}</h2>
        <span className="status-pill">
          {submission?.is_submitted ? "Submitted" : canSubmit ? "Open" : "Closed"}
        </span>
      </div>
      {selected.due_at && (
        <p className="muted">Due {new Date(selected.due_at).toLocaleString()}</p>
      )}
      {selected.instructions && (
        <div className="submission-content">{selected.instructions}</div>
      )}
      {submission?.is_submitted && (
        <Notice kind="success">
          Your work has been submitted{submission.locked ? " and is locked because peer reviews have been allocated." : "."}
          {!submission.locked && selected.status === "open" && !pastDue
            ? " You can update it until reviews are allocated."
            : ""}
        </Notice>
      )}
      {!canSubmit && !submission?.locked && (
        <Notice>
          {selected.status !== "open"
            ? "This assignment is closed and no longer accepts submissions."
            : pastDue
              ? "The due date has passed; this assignment no longer accepts submissions."
              : "This assignment is not currently accepting submissions."}
        </Notice>
      )}
      {submission?.file_url && (
        <p>
          Current attachment:{" "}
          <a href={submission.file_url} target="_blank" rel="noreferrer">
            {submission.original_file_name || "View submitted file"}
          </a>
        </p>
      )}
      <form className="stack" onSubmit={send}>
        <fieldset disabled={!canSubmit} className="submission-fields">
          <label>
            Submission title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Your work
            <textarea
              rows={9}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </label>
          <label>
            Attach a file
            <input
              type="file"
              accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </fieldset>
        {submission?.file_url && canSubmit && (
          <p className="muted">
            Leave the file field empty to keep your current attachment; selecting a new file replaces it.
          </p>
        )}
        {validation && <Notice kind="error">{validation}</Notice>}
        {canSubmit && (
          <>
            <p className="muted">Submit text, an attachment, or both. Accepted files: PDF, TXT, DOC, DOCX, PNG, JPG (10 MB maximum).</p>
            <Button>{submission?.is_submitted ? "Update submission" : "Submit work"}</Button>
          </>
        )}
      </form>
    </section>
    )}
    </>
  );
}
function Backup({ onError }: { onError: (s: string) => void }) {
  async function download() {
    try {
      const r = await fetch("/api/exports/backup", {
        headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
      });
      if (!r.ok) throw new Error(`Backup download failed (${r.status}).`);
      const b = await r.blob();
      const url = URL.createObjectURL(b);
      const a = document.createElement("a");
      a.href = url;
      a.download = "peer-review-backup.sqlite";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      onError(messageOf(e));
    }
  }
  return (
    <Button className="secondary" onClick={() => void download()}>
      Download backup
    </Button>
  );
}
