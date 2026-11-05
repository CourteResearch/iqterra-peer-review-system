"""FastAPI application for the local-first peer-review platform."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import database
from app.database import init_db
from app.routers import assignments, auth, courses, exports, groups, misc, overview, reviews, students

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
INDEX_FILE = PROJECT_DIR / "frontend" / "dist" / "index.html"
if not INDEX_FILE.exists():
    INDEX_FILE = BASE_DIR / "static" / "index.html"
ASSETS_DIR = PROJECT_DIR / "frontend" / "dist" / "assets"
DATA_DIR = database.DATA_DIR


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(
    title="IQ-T02 Peer-Review Platform",
    version="2.0.0",
    lifespan=lifespan,
)

for module in (auth, courses, groups, students, assignments, reviews, overview, exports, misc):
    app.include_router(module.router)


@app.get("/")
def root():
    if not INDEX_FILE.exists():
        raise HTTPException(404, "Frontend build is not present")
    return FileResponse(INDEX_FILE, media_type="text/html")


@app.get("/health")
def health():
    return {"status": "ok"}


if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend-assets")
