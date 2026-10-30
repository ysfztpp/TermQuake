import shutil
import sqlite3
from pathlib import Path

import pytest

from termquake.cli import run_import
from termquake.config import REPO_ROOT, Paths, load_config

FIXTURE_SHEET = Path(__file__).parent / "fixtures" / "legacy"


@pytest.fixture
def config():
    return load_config(REPO_ROOT / "termquake.toml")


@pytest.fixture
def workspace(tmp_path) -> Paths:
    """An isolated copy of the repository layout, so tests never touch the real data."""
    (tmp_path / "db").mkdir()
    shutil.copy(REPO_ROOT / "db" / "schema.sql", tmp_path / "db" / "schema.sql")
    shutil.copytree(FIXTURE_SHEET, tmp_path / "data" / "legacy")
    shutil.copy(REPO_ROOT / "termquake.toml", tmp_path / "termquake.toml")
    return Paths(tmp_path)


@pytest.fixture
def imported(config, workspace) -> Paths:
    """Workspace after `termquake import-sheet` (which also builds the database)."""
    run_import(config, workspace, force=False)
    return workspace


def query(paths: Paths, sql: str, *args):
    conn = sqlite3.connect(paths.database)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def execute(paths: Paths, *statements: str) -> None:
    conn = sqlite3.connect(paths.database)
    conn.execute("PRAGMA foreign_keys = ON")
    for sql in statements:
        conn.execute(sql)
    conn.commit()
    conn.close()
