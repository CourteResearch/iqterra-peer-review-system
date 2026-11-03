# Local data, backup, restore, and reset

The app keeps active data in `data/` by default:

- `data/iqterra.sqlite3` — accounts, assignments, questions, submissions, allocations, reviews, and moderation history.
- `data/uploads/` — student attachments, stored under generated filenames.

The supplied root `iqt02.db` is a historical starter/reference database; the running app does not modify it. The application accepts PDF, DOCX, TXT, Markdown, and RTF attachments up to 10 MB each. The instructor backup downloads a ZIP containing a consistent SQLite snapshot and the files currently in `data/uploads/`.

## Make a backup

Sign in as an instructor and use **Download backup**. Keep the resulting `iqterra-backup.zip` in a secure location. It can contain student names, submissions, review text, and attachments; do not send it through public or untrusted channels.

You can also copy the complete `data/` directory while the application is stopped. The ZIP builder in the project root creates a full source-and-data transfer archive:

```sh
python scripts/build_download_bundle.py
```

That archive includes the current SQLite database and uploads if they exist, but excludes `.env`, dependency folders, caches, and `.git`. Do not add `.env` or passwords to any ZIP.

## Restore an instructor backup

1. Stop FastAPI or stop the local Compose service. Do not replace a live SQLite file; SQLite may be using its WAL files.
2. Copy the current `data/` directory somewhere safe before replacing anything.
3. Extract `iqterra-backup.zip` to a temporary folder. It should contain `iqterra.sqlite3` and may contain an `uploads/` folder.
4. Replace `data/iqterra.sqlite3` with the extracted database. Restore the extracted `uploads/` files into `data/uploads/`.
5. Start the app again and sign in with an account present in the restored database.

macOS/Linux example, from the project root:

```sh
mkdir -p /tmp/iqterra-restore
unzip -o /path/to/iqterra-backup.zip -d /tmp/iqterra-restore
mkdir -p data/uploads
cp /tmp/iqterra-restore/iqterra.sqlite3 data/iqterra.sqlite3
if [ -d /tmp/iqterra-restore/uploads ]; then cp -a /tmp/iqterra-restore/uploads/. data/uploads/; fi
```

Windows PowerShell example, after stopping the app:

```powershell
New-Item -ItemType Directory -Force .\restore-temp | Out-Null
Expand-Archive -Path .\iqterra-backup.zip -DestinationPath .\restore-temp -Force
New-Item -ItemType Directory -Force .\data\uploads | Out-Null
Copy-Item .\restore-temp\iqterra.sqlite3 .\data\iqterra.sqlite3 -Force
if (Test-Path .\restore-temp\uploads) {
  Copy-Item .\restore-temp\uploads\* .\data\uploads\ -Recurse -Force
}
```

If `.env` sets `IQT02_DATABASE_PATH` or `IQT02_DATA_DIR`, restore to those configured paths instead of the defaults above. With Docker Compose, stop the app using `docker compose down`; the `./data` bind mount remains on the host.

## Reset the synthetic demo

Reset discards all active local accounts, student work, and review history. First make a backup, then stop the application and move the complete `data/` directory aside rather than deleting it. Start with a new empty `data/` and run:

```sh
python -m app.seed_demo
python -m app.bootstrap
```

The seed command refuses to replace a populated database. It creates ten fictional students, one example assignment, five prompts, sample submissions, and the starter review allocation. The bootstrap command creates a new instructor account interactively. The root `iqt02.db` is not part of reset.

## Local versus hosted persistence

When run natively, or through Compose with the supplied bind mount, the SQLite database and uploads are ordinary files on your computer. A Manus Preview session is a review environment, not a durable public production database. The project does not enable the Manus-managed database and does not claim that container-local SQLite survives a published container replacement.
