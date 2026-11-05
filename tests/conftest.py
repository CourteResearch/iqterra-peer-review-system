"""Test isolation: set secrets before app imports and redirect every DB/data path."""

import os
import pytest

os.environ["IQT02_JWT_SECRET"] = "test-only-secret-not-for-production-123456789"


@pytest.fixture(autouse=True)
def isolated_sqlite(tmp_path, monkeypatch):
    from app import database

    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "isolated.sqlite3")
    monkeypatch.setattr(database, "DATA_DIR", tmp_path / "data")
    from app import main

    monkeypatch.setattr(main, "DATA_DIR", tmp_path / "data")
    return tmp_path
