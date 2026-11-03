# TODO

## Completed groundwork

- [x] **Original FastAPI starter preserved:** kept the original backend files and the supplied `iqt02.db` reference database unchanged.
- [x] **Uploaded frontend staged:** extracted the React/Vite frontend into `frontend/` in the same project folder as the Python backend in `app/`.
- [x] **Integrated Manus Preview:** FastAPI serves the built React app on port 3000; the synthetic SQLite demo contains 10 students, one assignment, 10 submissions, and 30 allocations, and the instructor overview and anonymous student review detail respond to read-only Preview requests.

## Approved implementation outcomes

- [ ] **One local project and downloadable package**
  - Keep the frontend and backend in one project folder, clearly labelled as `frontend/` and `app/`.
  - Include all source and the active local SQLite data needed to run the project after download.
  - Provide local setup/run instructions and a ZIP that excludes secrets, VCS internals, dependency caches, and `node_modules`.
  - Keep the original root `iqt02.db` reference data unchanged; use a separate, clearly named active database for the 10-student demo.
  - Keep Manus's managed database disabled and do not publish the site as part of this work.

- [ ] **Instructor accounts, roster, and assignment authoring**
  - Preserve secure password hashing and add an instructor bootstrap flow suitable for local installation.
  - Let an instructor create student accounts/roster entries and manage assignment setup; the initial synthetic demo cohort has 10 students, without hard-coding a permanent 10-student product limit.
  - Let the instructor create an assignment with a title, instructions, submission window, and exactly five editable Likert-style questions selected from question templates.
  - Use a five-point response scale with clear endpoint labels for each Likert question.
  - Lock the question wording/scale after a review has been submitted so existing review scores keep their original meaning.

- [ ] **Submissions and fair peer-review allocation**
  - Let enrolled students submit assignment work as text and/or supported files stored locally with safe filenames and documented size/type limits.
  - Generate and save assignment-specific reviewer/submission pairs using a balanced workload and the existing default of three reviewers per submission where cohort size permits.
  - Prevent a student from reviewing their own submission, from receiving the same reviewer/submission pair twice, from reviewing the same submission twice, or from forming reciprocal pairs.
  - Give each submission the configured number of distinct reviewers and reject invalid cohorts/configurations rather than saving partial or invalid allocations.
  - Save allocation changes transactionally; never silently delete or replace submitted reviews, and prevent reallocation after review work has started unless an instructor explicitly reopens the round.

- [ ] **Student review workflow and privacy**
  - Show each authenticated student only the submissions assigned to them, without exposing reviewer or author identities to other students.
  - Let a student score all five assignment questions, save a draft, and submit the allocated review once.
  - Enforce assignment membership, review ownership, required scores, submission state, and the no-duplicate rule on the server as well as in the UI.
  - Keep instructor-only review details and moderation actions inaccessible to student accounts.

- [ ] **Instructor overview, moderation, and export**
  - Show real SQLite-backed counts and progress for enrolled students, submissions, allocations, completed/pending reviews, reviewer workloads, and question-level outcomes.
  - Let instructors review flagged submissions/reviews, record an approve/dismiss decision and note, and retain an audit history.
  - Replace frontend-only fake success actions with saved backend operations or remove/label actions that are not available.
  - Let the instructor download a consistent SQLite backup and locally stored submission files/data export.

- [ ] **SQLite lifecycle and local operation**
  - Store active application data under `data/`, with foreign-key enforcement, unique constraints, safe transaction boundaries, concurrency settings, and versioned additive migrations.
  - Include a clearly labelled 10-student synthetic demo seed without overwriting user edits on restart.
  - Use temporary isolated SQLite files for automated tests; never point tests or destructive setup commands at the active database or the original reference database.
  - Provide a local Docker Compose bind mount for persistent user-machine data and document that the WebDev published container's writable filesystem is temporary, so durable hosted production is not claimed with SQLite alone.

- [ ] **Moodle boundary and honest product state**
  - Do not claim a live Moodle connection, roster import, or grade passback without a Moodle site and its LTI/NRPS/AGS registration details.
  - Show Moodle integration as not configured and keep external Moodle/grade requests disabled until configuration is supplied.

- [ ] **Automated checks and handoff**
  - Run the existing and new allocation, authorization, assignment, review, moderation, backup/export, and local-start checks against isolated synthetic/test databases.
  - Start the completed application in Manus Preview on the configured port and verify the route manifest.
  - Save a downloadable project ZIP and document where the live SQLite file and uploads are stored.
