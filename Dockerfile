# Build the React frontend with the project-pinned package manager.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /src
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./frontend/
COPY frontend/ ./frontend/
RUN pnpm --dir frontend install --frozen-lockfile \
    && pnpm --dir frontend run build

# Run the FastAPI backend and serve its built frontend from one origin.
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    IQT02_DATABASE_PATH=/app/data/iqterra.sqlite3 \
    IQT02_UPLOAD_DIR=/app/data/uploads
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY --from=frontend-build /src/frontend/dist ./frontend/dist
COPY frontend/public/manus-routes.json ./frontend/public/manus-routes.json
COPY public/manus-routes.json ./public/manus-routes.json
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/uploads \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
