"""Build, save and migrate the SQL database.

    data/db/*.sql  --build-->  build/termquake.db  --(edit with SQL / scripts / GUI)-->  --dump-->  data/db/*.sql

* build:   create build/termquake.db from db/schema.sql + data/db/*.sql, install
           the history triggers, run the QA checks.
* dump:    write the (edited) database back to data/db/*.sql and refresh
           data/QA_REPORT.md. Commit the result; CI rebuilds and redeploys.
* migrate: one-time creation of data/db from the legacy sheet snapshot.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import SCHEMA_VERSION, dbio, qa
from .config import Config, Paths
from .legacy import MigrationStats, migrate_into, write_migration_report
from .textnorm import fold


class BuildError(RuntimeError):
    """The database cannot be built or saved safely."""


@dataclass
class BuildResult:
    concepts: int
    terms: dict[str, int]
    definitions: int
    issues: dict[str, int]


def _create_schema(conn: sqlite3.Connection, paths: Paths) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((paths.db_dir / "schema.sql").read_text(encoding="utf-8"))


def _finish(conn: sqlite3.Connection, paths: Paths) -> None:
    # History starts after loading, so a rebuild never logs the load itself as edits.
    conn.executescript((paths.db_dir / "triggers.sql").read_text(encoding="utf-8"))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        raise BuildError(f"foreign key violations: {problems[:5]}")


def refresh_search_keys(conn: sqlite3.Connection) -> int:
    """Recompute term.text_norm after edits (SQL can't run the fold function)."""
    stale = [
        (fold(text), tid)
        for tid, text, norm in conn.execute("SELECT id, text, text_norm FROM term").fetchall()
        if fold(text) != norm
    ]
    conn.executemany("UPDATE term SET text_norm = ? WHERE id = ?", stale)
    return len(stale)


def _summary(conn: sqlite3.Connection, issues: dict[str, int]) -> BuildResult:
    return BuildResult(
        concepts=conn.execute("SELECT COUNT(*) FROM concept").fetchone()[0],
        terms=dict(
            conn.execute("SELECT lang, COUNT(*) FROM term GROUP BY lang ORDER BY lang").fetchall()
        ),
        definitions=conn.execute("SELECT COUNT(*) FROM definition").fetchone()[0],
        issues=issues,
    )


def build_database(config: Config, paths: Paths, out: Path | None = None) -> BuildResult:
    out = out or paths.database
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        _create_schema(conn, paths)
        try:
            dbio.load(conn, paths.data_db)
        except FileNotFoundError as exc:
            raise BuildError(str(exc)) from exc
        if stale := refresh_search_keys(conn):
            raise BuildError(
                f"{stale} terms have an outdated text_norm; run `termquake dump` and commit."
            )
        _finish(conn, paths)
        issues = qa.run_checks(conn, config)
        conn.commit()
        conn.execute("ANALYZE")
        conn.commit()
        result = _summary(conn, issues)
    finally:
        conn.close()
    tmp.replace(out)
    return result


def dump_database(config: Config, paths: Paths, *, check: bool = False) -> list[str]:
    """Save build/termquake.db to data/db/*.sql and data/QA_REPORT.md.

    With check=True nothing is written; returns the files that would change
    (CI uses this to prove the committed files are canonical and up to date).
    """
    if not paths.database.exists():
        raise BuildError("build/termquake.db not found. Run `termquake build` first.")
    conn = sqlite3.connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise BuildError("Database schema version mismatch; rebuild with `termquake build`.")
        refresh_search_keys(conn)
        qa.run_checks(conn, config)
        conn.commit()
        report = paths.qa_report
        tmp_report = report.with_suffix(".tmp")
        qa.write_report(conn, config, tmp_report)
        if check:
            stale = dbio.diff(conn, paths.data_db)
            current = report.read_text(encoding="utf-8") if report.exists() else None
            if current != tmp_report.read_text(encoding="utf-8"):
                stale.append(report.name)
            tmp_report.unlink()
            return stale
        dbio.dump(conn, paths.data_db)
        tmp_report.replace(report)
        return []
    finally:
        conn.close()


def migrate(config: Config, paths: Paths, *, force: bool = False) -> MigrationStats:
    """One-time: create data/db from the legacy sheet snapshot in data/legacy."""
    if any(paths.data_db.glob("*.sql")) and not force:
        raise BuildError(
            "data/db already exists: the SQL database is the source of truth now. "
            "Re-running the migration would overwrite every edit made since. "
            "Use --force only if you really mean to start over from the legacy sheet."
        )
    conn = sqlite3.connect(":memory:")
    try:
        _create_schema(conn, paths)
        stats = migrate_into(
            conn, config, paths.legacy, (paths.db_dir / "seed.sql").read_text(encoding="utf-8")
        )
        refresh_search_keys(conn)
        conn.commit()
        for stale in paths.data_db.glob("*.sql"):
            stale.unlink()
        dbio.dump(conn, paths.data_db)
    finally:
        conn.close()
    write_migration_report(stats, paths.legacy / "MIGRATION_REPORT.md")
    build_database(config, paths)
    dump_database(config, paths)  # writes data/QA_REPORT.md
    return stats
