import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  api,
  Assignment,
  getToken,
  list,
  ModerationItem,
  OverviewData,
  Question,
  Review,
  setToken,
  Submission,
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
  | "assignments"
  | "roster"
  | "allocation"
  | "moderation"
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
          <b>Peer review workspace</b>
          <small>Local course</small>
        </div>
        <nav className="main-nav" aria-label="Workspace navigation">
          {(instructor
            ? [
                ["overview", "Overview"],
                ["assignments", "Assignments"],
                ["roster", "Student roster"],
                ["allocation", "Allocation"],
                ["moderation", "Moderation"],
              ]
            : [
                ["reviews", "Reviews to complete"],
                ["submit", "Submit work"],
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
          {instructor ? (
            screen === "overview" ? (
              <Overview
                run={run}
                assignmentId={assignmentId}
                onAssignment={setAssignmentId}
                onNavigate={setScreen}
              />
            ) : screen === "assignments" ? (
              <Assignments run={run} onSuccess={setSuccess} />
            ) : screen === "roster" ? (
              <Roster run={run} onSuccess={setSuccess} />
            ) : screen === "allocation" ? (
              <Allocation run={run} onSuccess={setSuccess} />
            ) : (
              <Moderation run={run} onSuccess={setSuccess} />
            )
          ) : screen === "submit" ? (
            <SubmissionForm run={run} onSuccess={setSuccess} />
          ) : (
            <MyReviews run={run} onSuccess={setSuccess} />
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
          assignments: "Assignments",
          roster: "Student roster",
          allocation: "Review allocation",
          moderation: "Moderation",
        } as Record<string, string>
      )[screen]
    : screen === "submit"
      ? "Submit your work"
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
) {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const refresh = useCallback(
    () =>
      run<Assignment[] | { items?: Assignment[]; results?: Assignment[] }>(
        () => api("/assignments"),
        (v) => setAssignments(list(v)),
      ),
    [run],
  );
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { assignments, refresh };
}
function Overview({
  run,
  assignmentId,
  onAssignment,
  onNavigate,
}: {
  run: Action;
  assignmentId: string;
  onAssignment: (v: string) => void;
  onNavigate: (v: Screen) => void;
}) {
  const { assignments } = useAssignments(run);
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
function Assignments({
  run,
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const { assignments, refresh } = useAssignments(run);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<Assignment | null>(null);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [due, setDue] = useState("");
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
                  {a.due_at
                    ? new Date(a.due_at).toLocaleString()
                    : "No due date"}{" "}
                  · {a.status || "Draft"}
                </small>
              </div>
              <Button onClick={() => start(a)}>Edit draft</Button>
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
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const [students, setStudents] = useState<import("./api").Student[]>([]);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [credential, setCredential] = useState("");
  const [copied, setCopied] = useState(false);
  const load = useCallback(
    () =>
      run<any>(
        () => api("/students"),
        (v) => setStudents(list(v)),
      ),
    [run],
  );
  useEffect(() => {
    void load();
  }, [load]);
  async function add(e: FormEvent) {
    e.preventDefault();
    const x = await run(() =>
      api<import("./api").StudentCreated>("/students", {
        method: "POST",
        body: JSON.stringify({ display_name: name, username }),
      }),
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
      {credential && <section className="credential-panel" aria-labelledby="credential-title"><div><h2 id="credential-title">One-time student credential</h2><p>Share this credential privately with the student. It is shown only once and is not stored by this page.</p><code>{credential}</code></div><div className="action-row"><Button onClick={() => { void navigator.clipboard.writeText(credential).then(() => setCopied(true)).catch(() => onSuccess("Select and copy the credential manually; clipboard access was unavailable.")); }}> {copied ? "Copied" : "Copy credential"}</Button><Button className="secondary" onClick={() => setCredential("")}>Dismiss</Button></div></section>}
      <section className="panel">
        <h2>
          Roster <span className="muted">({students.length})</span>
        </h2>
        {students.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Username</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td>{s.display_name}</td>
                    <td>{s.username}</td>
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
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run);
  const [assignmentId, setAssignment] = useState("");
  const [count, setCount] = useState(3);
  const [items, setItems] = useState<any[]>([]);
  const active = assignmentId || String(assignments[0]?.id || "");
  useEffect(() => {
    if (active)
      void run<any>(
        () => api(`/allocations?assignment_id=${encodeURIComponent(active)}`),
        (v) => setItems(list(v)),
      );
  }, [active, run]);
  async function allocate() {
    const r = await run(() =>
      api(`/assignments/${active}/allocations`, {
        method: "POST",
        body: JSON.stringify({ reviewers_per_submission: count }),
      }),
    );
    if (r !== undefined) {
      onSuccess("Allocation generated.");
      setItems(list(r as any));
    }
  }
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
              Reviewers per submission{" "}
              <input
                type="number"
                min="1"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              />
            </label>
            <Button disabled={!active} onClick={allocate}>
              Generate allocation
            </Button>
          </div>
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
                      <td>{x.reviewer_name || x.reviewer || "—"}</td>
                      <td>{x.submission_title || x.submission_id || "—"}</td>
                      <td>{x.status || "Allocated"}</td>
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
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run);
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
function MyReviews({
  run,
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [active, setActive] = useState<Review | null>(null);
  const load = useCallback(
    () =>
      run<any>(
        () => api("/my/reviews"),
        (v) => setReviews(list(v)),
      ),
    [run],
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
  onSuccess,
}: {
  run: Action;
  onSuccess: (s: string) => void;
}) {
  const { assignments } = useAssignments(run);
  const [assignmentId, setAid] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState("");
  const activeAssignmentId = assignmentId || String(assignments[0]?.id || "");
  async function send(e: FormEvent) {
    e.preventDefault();
    if (!content.trim() && !file) { setValidation("Add text or choose a file before submitting."); return; }
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
      onSuccess("Submission received.");
    }
  }
  return (
    <section className="panel">
      <h2>Submit your work</h2>
      {assignments.length ? (
        <form className="stack" onSubmit={send}>
          <label>
            Assignment
            <select
              value={activeAssignmentId}
              onChange={(e) => setAid(e.target.value)}
            >
              {assignments.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Submission title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Content
            <textarea
              rows={9}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </label>
          <label>
            Optional file
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
          {validation && <Notice kind="error">{validation}</Notice>}
          <p className="muted">Provide text, a file, or both.</p>
          <Button>Submit work</Button>
        </form>
      ) : (
        <Empty>No assignments are available for submission.</Empty>
      )}
    </section>
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
