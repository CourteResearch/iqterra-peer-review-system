# IQTerra Peer Review

A local-first peer-review application with a React/TypeScript interface and FastAPI/Python backend. The project uses a local SQLite file and keeps the frontend and backend together in this folder: `frontend/` and `app/`.

The workflow supports instructor accounts, assignments with five editable Likert questions, a ten-student synthetic demo cohort, student submissions and anonymous assigned reviews, balanced review allocation, moderation, and local data backup/export. The demo students are fictional; ten is the example cohort size, not a permanent roster limit.

## Important boundaries

- **All active application data is local:** SQLite is stored at `data/iqterra.sqlite3` by default, and submission files are stored in `data/uploads/`. Docker Compose bind-mounts `data/` so those files remain on the computer running Docker.
- The original `iqt02.db` at the project root is the untouched starter/reference database. The running application uses the separate active database under `data/`.
- Manus-managed database stays disabled. Do not publish this SQLite version as a durable cloud database: the WebDev published container's writable filesystem is temporary. For reliable hosted multi-instance production use, a later persistent database/storage decision is required.
- **Moodle is not connected.** This project does not have a Moodle URL, LTI registration, roster credentials, or grade-passback configuration. The app will not claim a live Moodle connection or send scores to Moodle. Moodle integration is a separate future configuration/implementation.
- The download bundle includes the database and uploaded files, which may contain student information if you add real data. Store and share that ZIP securely; never include `.env` or plaintext credentials. Demo/bootstrap passwords are kept in a separate private handout and should not be posted publicly.

## Requirements

For a direct local run, install Python 3.11+ and Node.js 22+ with Corepack enabled. Alternatively, use Docker Desktop and Docker Compose v2.

## Run locally with Python and Node

Open this project folder in a terminal. Create a local environment file from the safe template and set a unique random signing secret; do not commit `.env`:

```sh
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `IQT02_JWT_SECRET` in `.env`. On Windows PowerShell use `Copy-Item .env.example .env`, then generate a value with `py -c "import secrets; print(secrets.token_urlsafe(48))"` and paste it into the local `.env` file.

Create the Python environment and build the frontend:

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell instead: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
corepack enable
corepack prepare pnpm@11.25.0 --activate
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend run build
```

Initialize the sample workspace and create the first instructor account:

```sh
python -m app.seed_demo
python -m app.bootstrap
```

The demo seeder refuses to overwrite a populated database. It creates ten synthetic student logins and prints their randomized initial passwords once in the terminal; distribute those values privately, because they are not stored as plaintext for later retrieval. The bootstrap command prompts you to create the first instructor. There is no shared/default instructor password. For a real class roster, the instructor can create accounts and provide each student their login details through a secure channel.

Start the single-server application from the project root:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

Open `http://127.0.0.1:8000/`. The JSON health check is at `/health`; interactive API documentation is at `/docs`. The frontend and API are served from one origin in this built mode.

For frontend development with hot reload, keep FastAPI running on port 8000 and use a second terminal:

```sh
pnpm --dir frontend dev -- --host 127.0.0.1 --port 5173
```

Then open `http://127.0.0.1:5173/`. Vite proxies `/api` and `/health` to FastAPI.

## Run locally with Docker Compose

Copy `.env.example` to `.env`, set a strong random `IQT02_JWT_SECRET`, then build and start the app:

```sh
docker compose up --build -d
```

Create the sample workspace and instructor account inside the running service:

```sh
docker compose exec app python -m app.seed_demo
docker compose exec app python -m app.bootstrap
```

Open `http://localhost:8000/`. Docker Compose binds the local `./data` directory to `/app/data`; the active database and uploaded files remain ordinary files in your project folder. Keep a backup of `data/` and use the in-app instructor backup/export action before important changes. Do not delete `data/` if you want to keep your work.

## Demo behavior

The synthetic demo contains ten fictional students, one example assignment, five starter Likert prompts, sample text submissions, and a three-review-per-submission allocation where the cohort allows it. Students are assigned only peer work: the server checks for self-review, duplicate assignments, and reciprocal reviewer pairs before saving allocations. The seed command prints each demo account's random initial password once; the instructor can also add separate real roster accounts.

Assignments begin available for the local workflow. Instructors can edit the five prompts before reviews are submitted. Once a review is submitted, the rubric is locked to preserve the meaning of scores. Students can save review drafts and submit each assigned review once. Instructor overview and moderation data come from SQLite, not hard-coded frontend placeholders.

## Data, backups, and download

The normal active data paths are:

- `data/iqterra.sqlite3` — current assignments, roster, submissions, review allocations, answers, and moderation records.
- `data/uploads/` — locally stored submission attachments.
- `iqt02.db` — the original supplied starter/reference database, preserved but not used by the new app.

The instructor backup action creates a consistent local data backup. To package the complete source and current local data for download, run:

```sh
python scripts/build_download_bundle.py
```

The ZIP is created one directory above this project as `iqterra-peer-review-local.zip`. It includes the active SQLite snapshot and local uploads, while excluding `.env`, `.git`, dependency directories, caches, and frontend build output. The archive is for local transfer; treat it as confidential if it contains real student work.

For safe restore/reset steps on macOS/Linux and Windows PowerShell, see [docs/data-and-restore.md](docs/data-and-restore.md).

## Tests and frontend build

Run the tests against temporary isolated SQLite databases (not the active application DB):

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
pnpm --dir frontend run build
```

## Current integration limits

This is a self-contained peer-review workflow, not a verified LTI Advantage service. Moodle LTI 1.3 launch validation, roster retrieval through NRPS, and grade passback through AGS are not configured or active. The former PostgreSQL/RLS schema under `database/` is retained as clearly labelled starter reference material and is not used by this SQLite application.
