# IQTerra Peer Review — implementation plan

## Product scope

Turn the current static React mockup and FastAPI starter into one locally runnable peer-review application. Keep the code in one project folder with clear `frontend/` and `app/` boundaries. The new working flow will be instructor login → create an assignment and review form → enrol students and collect submissions → allocate peer reviews → students complete assigned reviews → instructor monitors completion and handles flags. The preview dataset will use ten fictional students; this is the starting/demo cohort, not a hard limit on future rosters.

Each new assignment will start with exactly five editable Likert-style criteria selected from a small template set. Each criterion will use a five-point scale with visible endpoint labels. Instructors can adjust the prompts before the assignment opens; the rubric becomes read-only after a review has been submitted so existing scores cannot be reinterpreted. Students can only access reviews assigned to them, score the five questions, save a draft, and submit once. A submitted review cannot be edited or duplicated unless an instructor explicitly reopens it.

The server, not the browser, will enforce role permissions, assignment state, reviewer/submission ownership, no self-review, no duplicate reviewer–submission pair, distinct reviewers, balanced loads, and no reciprocal pairs. Allocations will be generated per assignment, persisted in one transaction, and never silently replace submitted reviews. The instructor overview will use actual stored data for enrolled students, submissions, allocated/completed reviews, workload, question-level results, and moderation decisions. Moderation actions will be instructor-only and auditable. The existing frontend's fake export, save, Moodle-release, and audit actions will become real local operations or be removed/labelled as unavailable rather than reporting a false success.

Use a local SQLite file at `data/iqterra.sqlite3`, with foreign keys, unique constraints, WAL/busy timeout, transaction boundaries, and versioned additive migrations. Do not enable Manus's managed database. Preserve the existing root `iqt02.db` unchanged as the starter's 50-student reference database; create a clearly labelled active ten-student demo database and seed procedure separately. Add instructor-facing backup/export for the SQLite database and uploaded submission files. Include source, migrations, demo data, uploads required by the sample, and local run instructions in a downloadable ZIP; exclude `.env` secrets, VCS metadata, dependency caches, and `node_modules`.

Keep the existing Argon2 password hashing and JWT approach, but remove open student self-registration, add expiring tokens and server-side role checks on every protected route, and provide a safe local instructor-bootstrap flow. Instructor-created student accounts will receive one-time setup credentials/invitations rather than a universal default password. Store uploaded files beneath the local data directory using generated safe filenames, allow only documented file types/size limits, and authorize every download through the submission/assignment relationship.

This release is a self-contained local system. No Moodle site URL, LTI registration, signing keys, roster service, or grade-passback credentials were supplied, so the product must not claim to be connected to Moodle or send grades externally. Keep an explicit integration boundary and make the UI state that Moodle integration is not configured. Public deployment with SQLite is not included: the WebDev container's writable filesystem is temporary. A local Docker Compose setup will bind-mount the data directory for persistence on the user's computer; reliable hosted production persistence would require a later database/storage decision.

## Implementation and serving

Refactor the existing React/TypeScript UI into reusable view components and a typed API client. Keep its IQTerra identity and visual language, but make the dashboard values data-driven and replace local-only state with API requests. Vite will proxy `/api` to FastAPI during local development. The production/local single-server build will place the Vite output under `frontend/dist`, and FastAPI will serve that built application and the JSON page-route manifest from the same origin. Manus Preview will run FastAPI on the configured port 3000 against an isolated SQLite demo file; it will not touch a managed database.

Use the existing allocation engine as a starting point, but strengthen it for assignment-scoped cohorts and retain invariant checks both in service code and database uniqueness constraints. Organize API routers, Pydantic schemas, security, migrations, repositories/services, and allocation logic into readable modules. Pin Python and JavaScript runtime dependencies. Provide a Dockerfile and Docker Compose file for a single local app container with bind-mounted `data/`, plus a README covering Windows PowerShell and macOS/Linux setup, first instructor creation, demo mode, backups, reset/restore, and the Moodle boundary. Existing starter tests will run against temporary SQLite databases, never the user's active demo or reference database.

## Project structure

- `frontend/` — React/TypeScript screens, shared components, API client, Vite config, and static route manifest.
- `app/` — FastAPI app entrypoint; `routers/` for authentication, assignments, roster, submissions, allocations, reviews, moderation, overview, and exports; `schemas.py` for validated request shapes; `security.py` for account/password/token policy; `database.py` for SQLite connection management and inline versioned migrations; `helpers.py` for shared response queries; `allocation.py` for the pure allocation engine; `seed_demo.py` for synthetic data and instructor bootstrap.
- `data/` — active local SQLite database, local submission uploads, and generated backups; user data remains outside source code and is not deleted by migrations.
- `scripts/` — safe first-run/bootstrap, demo-seed, export, and local-run helpers.
- `tests/` — isolated unit/API tests using a temporary SQLite path.
- `docs/` — local data handling, operational notes, and the preserved starter's PostgreSQL/LTI reference material.
- Root `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md`, `TODO.md`, and this `plan.md` — local operation and project-level instructions.

## Design direction

Reuse and refine the existing IQTerra frontend rather than introducing an unrelated redesign.

- **Design Movement:** A restrained academic-workspace aesthetic with editorial typography and the clear information hierarchy of a mature SaaS admin tool.
- **Core Principles:** Make assignment setup explicit; keep student review tasks focused; show operational progress without clutter; use safe, clear confirmations for irreversible actions.
- **Color Philosophy:** Retain the warm paper-like background and ink/navy text, using the existing coral-orange as the ownable action color. Reserve muted green, amber, and rose for statuses so color communicates state rather than filling large blocks.
- **Layout Paradigm:** Keep the left navigation rail and broad workspace, but reduce oversized solid banners in favor of a clear assignment header, a compact five-step setup flow, and data-dense but breathable tables/cards.
- **Signature Elements:** A small coral IQTerra mark; calm status pills with textual labels; a five-question progress indicator reused in assignment setup and student reviews.
- **Interaction Philosophy:** Every save, allocation, submission, and moderation action gets a visible result; draft and final states are distinct; destructive or lock-in actions require an explanatory confirmation.
- **Animation:** Use restrained 120–180 ms transitions for navigation, dialogs, and feedback; avoid decorative movement and honor reduced-motion preferences.
- **Typography System:** Preserve the supplied DM Sans / Manrope pairing, with accessible system fallbacks and consistent heading, body, label, and numeric hierarchies.
- **Brand Essence:** A practical peer-assessment workspace that helps instructors run fair, traceable reviews; **clear, fair, dependable**.
- **Brand Voice:** Plain, supportive, and specific. Example lines: “Five prompts. A clearer review.” and “Your assigned reviews never include your own submission.”
- **Wordmark & Logo:** Keep the existing IQTerra wordmark and supplied project mark; do not add generic stock imagery.
- **Signature Brand Color:** IQTerra coral-orange from the existing interface, reserved for primary actions and progress emphasis.

## Boundaries

The user selected SQLite and local/downloadable files over the managed database. The application can be fully functional and persistent when run on the user's local machine with the provided bind mount, but this project will not be represented as durable public cloud production while hosted writable storage remains ephemeral. Live Moodle LTI/roster/grade passback remains unconfigured until a Moodle instance and its registration details are available. Do not publish the site or send any Moodle/grade data as part of this implementation.
