"""The teaching queries in queries/ must keep working as the data changes."""

import sqlite3

import pytest

from termquake.config import REPO_ROOT

QUERIES = sorted((REPO_ROOT / "queries").glob("*.sql"))


def statements(sql: str) -> list[str]:
    code = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [s.strip() for s in code.split(";") if s.strip()]


def test_there_are_queries():
    assert len(QUERIES) >= 10


@pytest.mark.parametrize("path", QUERIES, ids=lambda p: p.name)
def test_query_runs(imported, path):
    conn = sqlite3.connect(imported.database)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        for sql in statements(path.read_text("utf-8")):
            conn.execute(sql).fetchall()
    finally:
        conn.rollback()  # example edits are never kept
        conn.close()
