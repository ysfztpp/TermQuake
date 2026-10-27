"""Build, save and migrate the SQL database.

    data/db/*.sql  --build-->  build/termquake.db  --(edit with SQL / scripts / GUI)-->  --dump-->  data/db/*.sql

* build:   create build/termquake.db from db/schema.sql + data/db/*.sql, compute
           the derived data (search keys, QA findings), install the history
           triggers. Refuses to replace a database that has unsaved edits.
* dump:    write the (edited) database back to data/db/*.sql and refresh
           data/QA_REPORT.md. Refuses if data/db changed since the build (a
           git pull, a branch switch, a hand edit), because that would undo
           those changes. Commit the result; CI rebuilds and redeploys.
* migrate: one-time creation of data/db from the legacy sheet snapshot.

The built database remembers which files it was built from (table build_info),
which is how build and dump can tell when one would overwrite the other.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import SCHEMA_VERSION, dbio, qa
from .config import Config, Paths
from .legacy import MigrationStats, migrate_into, write_migration_report
from .textnorm import fold

BUILD_INFO = "CREATE TABLE IF NOT EXISTS build_info (key TEXT PRIMARY KEY, value TEXT NOT NULL)"


class BuildError(RuntimeError):
    """The database cannot be built or saved safely."""


@dataclass
class BuildResult:
    concepts: int
    terms: dict[str, int]
    definitions: int
    issues: dict[str, int]


@dataclass
class DumpCheck:
    """What `dump --check` found: data files that are not canonical, and whether
    the committed QA report is out of date (a warning, not a failure)."""

    stale_files: list[str] = field(default_factory=list)
    report_stale: bool = False


# --------------------------------------------------------------------------- helpers


def _hashes(texts: dict[str, str]) -> dict[str, str]:
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in texts.items()}


def _info(conn: sqlite3.Connection, key: str) -> dict[str, str] | None:
    try:
        row = conn.execute("SELECT value FROM build_info WHERE key = ?", (key,)).fetchone()
    except sqlite3.OperationalError:  # built before build_info existed
        return None
    return json.loads(row[0]) if row else None


def _remember(
    conn: sqlite3.Connection, data_files: dict[str, str], db_files: dict[str, str]
) -> None:
    conn.execute(BUILD_INFO)
    conn.executemany(
        "INSERT OR REPLACE INTO build_info(key, value) VALUES (?, ?)",
        [
            ("data_files", json.dumps(data_files, sort_keys=True)),
            ("db_files", json.dumps(db_files, sort_keys=True)),
        ],
    )


def _changed(old: dict[str, str], new: dict[str, str]) -> list[str]:
    return sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))


def unsaved_edits(database: Path) -> list[str]:
    """Data files that would change if this database were dumped now, compared
    with the files it was built from: i.e. edits not yet saved to data/db."""
    if not database.exists():
        return []
    conn = sqlite3.connect(database)
    try:
        built = _info(conn, "db_files")
        if built is None:
            return []
        return _changed(built, _hashes(dbio.dump_texts(conn)))
    except sqlite3.DatabaseError:
        return []  # not a TermQuake database (or corrupt): nothing worth protecting
    finally:
        conn.close()


def _foreign_key_problems(conn: sqlite3.Connection) -> list[str]:
    return [
        f"{table} row {rowid} points to a {parent} that does not exist"
        for table, rowid, parent, _ in conn.execute("PRAGMA foreign_key_check").fetchall()
    ]


def _create_schema(conn: sqlite3.Connection, paths: Paths) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((paths.db_dir / "schema.sql").read_text(encoding="utf-8"))


def _finish(conn: sqlite3.Connection, paths: Paths) -> None:
    # History starts after loading, so a rebuild never logs the load itself as edits.
    conn.executescript((paths.db_dir / "triggers.sql").read_text(encoding="utf-8"))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    if problems := _foreign_key_problems(conn):
        raise BuildError("broken references in data/db: " + "; ".join(problems[:5]))


def refresh_search_keys(conn: sqlite3.Connection) -> int:
    """Recompute term.text_norm (derived; SQL can't run the fold function)."""
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


# --------------------------------------------------------------------------- commands


def build_database(
    config: Config, paths: Paths, out: Path | None = None, *, force: bool = False
) -> BuildResult:
    out = out or paths.database
    if not force and (unsaved := unsaved_edits(out)):
        raise BuildError(
            f"{out.name} has edits that are not saved to data/db/ ({', '.join(unsaved)}). "
            "Run `termquake dump` to save them first, or `termquake build --force` to discard them."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        _create_schema(conn, paths)
        try:
            data_files = _hashes(dbio.read_texts(paths.data_db))
            dbio.load(conn, paths.data_db)
        except FileNotFoundError as exc:
            raise BuildError(str(exc)) from exc
        except dbio.DataFileError as exc:
            raise BuildError(str(exc)) from exc
        refresh_search_keys(conn)  # derived: never stored in data/db
        _finish(conn, paths)
        issues = qa.run_checks(conn, config)
        _remember(conn, data_files, _hashes(dbio.dump_texts(conn)))
        conn.commit()
        conn.execute("ANALYZE")
        conn.commit()
        result = _summary(conn, issues)
    finally:
        conn.close()
    tmp.replace(out)
    return result


def dump_database(
    config: Config, paths: Paths, *, check: bool = False, force: bool = False
) -> DumpCheck:
    """Save build/termquake.db to data/db/*.sql and data/QA_REPORT.md.

    With check=True nothing is written; returns what is out of date (CI uses
    this to prove the committed files are canonical).
    """
    if not paths.database.exists():
        raise BuildError("build/termquake.db not found. Run `termquake build` first.")
    conn = sqlite3.connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise BuildError("Database schema version mismatch; rebuild with `termquake build`.")
        if not check and not force:
            built_from = _info(conn, "data_files")
            on_disk = _hashes(dbio.read_texts(paths.data_db))
            if built_from is not None and (changed := _changed(built_from, on_disk)):
                raise BuildError(
                    f"data/db/ changed after build/termquake.db was built ({', '.join(changed)}), "
                    "for example by a git pull, a branch switch or a hand edit. Saving now would "
                    "undo those changes. Run `termquake build` to load them first (then redo any "
                    "database edits), or `termquake dump --force` to overwrite them on purpose."
                )
        if problems := _foreign_key_problems(conn):
            raise BuildError(
                "the database has broken references, so it cannot be saved: "
                + "; ".join(problems[:5])
            )
        refresh_search_keys(conn)
        qa.run_checks(conn, config)
        conn.commit()
        report = paths.qa_report
        tmp_report = report.with_suffix(".tmp")
        qa.write_report(conn, config, tmp_report)
        if check:
            current = report.read_text(encoding="utf-8") if report.exists() else None
            result = DumpCheck(
                stale_files=dbio.diff(conn, paths.data_db),
                report_stale=current != tmp_report.read_text(encoding="utf-8"),
            )
            tmp_report.unlink()
            return result
        files = _hashes(dbio.dump(conn, paths.data_db))
        tmp_report.replace(report)
        _remember(conn, files, files)  # the database and data/db now match
        conn.commit()
        return DumpCheck()
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
    build_database(config, paths, force=True)  # starting over is the point of migrate
    dump_database(config, paths)  # writes data/QA_REPORT.md
    return stats
