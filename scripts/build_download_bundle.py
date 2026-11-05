"""Create a portable source-and-data ZIP without copying secrets or live DB files."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "iqterra-peer-review-local.zip"
PREFIX = "IQTerra-Peer-Review/"
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".vite",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "__pycache__",
}
EXCLUDED_FILES = {".env", ".env.local", ".env.production", ".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo", "-wal", "-shm"}
CANONICAL_DATABASE = Path("data/iqterra.sqlite3")
CANONICAL_UPLOADS = Path("data/uploads")


def resolved_from_root(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def is_excluded(path: Path, active_database: Path, active_uploads: Path) -> bool:
    if path.is_symlink():
        return True
    relative = path.relative_to(ROOT)
    if set(relative.parts) & EXCLUDED_DIRS:
        return True
    resolved = path.resolve()
    if (
        resolved == active_database
        or resolved == active_database.with_name(active_database.name + "-wal")
        or resolved == active_database.with_name(active_database.name + "-shm")
    ):
        return True
    if relative == CANONICAL_DATABASE or inside(relative, CANONICAL_UPLOADS):
        return True
    if inside(resolved, active_uploads):
        return True
    if path.name in EXCLUDED_FILES or path.name.startswith(".env."):
        return path.name != ".env.example"
    return any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def main() -> None:
    data_dir = resolved_from_root(os.getenv("IQT02_DATA_DIR", "data"))
    database = resolved_from_root(
        os.getenv("IQT02_DATABASE_PATH", str(data_dir / "iqterra.sqlite3"))
    )
    uploads = (data_dir / "uploads").resolve()

    with tempfile.TemporaryDirectory(prefix="iqterra-export-") as temporary:
        snapshot = Path(temporary) / "iqterra.sqlite3"
        if database.is_file():
            source = sqlite3.connect(
                f"{database.as_uri()}?mode=ro", uri=True, timeout=15
            )
            destination = sqlite3.connect(snapshot)
            try:
                source.execute("PRAGMA query_only=ON")
                source.backup(destination)
            finally:
                destination.close()
                source.close()

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(ROOT.rglob("*")):
                if not path.is_file() or is_excluded(path, database, uploads):
                    continue
                archive.write(path, PREFIX + path.relative_to(ROOT).as_posix())

            if snapshot.exists():
                archive.write(snapshot, PREFIX + CANONICAL_DATABASE.as_posix())

            if uploads.is_dir():
                for path in sorted(uploads.rglob("*")):
                    if path.is_file() and not path.is_symlink():
                        relative = Path(CANONICAL_UPLOADS, path.relative_to(uploads))
                        archive.write(path, PREFIX + relative.as_posix())

            if data_dir != (ROOT / "data").resolve() and data_dir.is_dir():
                for path in sorted(data_dir.rglob("*")):
                    if (
                        path.is_file()
                        and not path.is_symlink()
                        and path.resolve() != database
                        and not inside(path.resolve(), uploads)
                    ):
                        relative = Path("data", path.relative_to(data_dir))
                        archive.write(path, PREFIX + relative.as_posix())

    print(f"Created {OUTPUT}")
    print(
        "Included project source, an SQLite snapshot, and local uploads; "
        "omitted .env, VCS metadata, dependencies, caches, and build output."
    )


if __name__ == "__main__":
    main()
