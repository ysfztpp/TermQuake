"""The database and its text form in git.

The SQL database is the source of truth. In git it is stored as one SQL file
per table (data/db/<table>.sql), one INSERT per row, ordered by id:

    data/db/*.sql  --build-->  build/termquake.db  --(edit: SQL, a GUI, a script)
         ^                                                   |
         +--------------------------dump---------------------+

* build: create build/termquake.db from db/schema.sql + data/db/*.sql.
* dump:  write the (edited) database back to data/db/*.sql; commit the result.

Two safety checks keep the two copies from overwriting each other's changes:
`build` won't discard edits that were not dumped, and `dump` won't undo
changes that reached data/db after the build (a git pull, a hand edit). They
compare fingerprints kept next to the database, in build/termquake.db.json.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import SCHEMA_VERSION
from .config import Paths

# Load and dump order: a table comes after the tables it refers to.
TABLES = ["domain", "entry", "term", "definition"]

HEADER = "-- TermQuake data: table {table}. Written by `termquake dump`; one row per line.\n"


class DatabaseError(RuntimeError):
    """The database cannot be built or saved safely. The message says what to do."""


@dataclass
class Counts:
    entries: int
    terms: dict[str, int]
    definitions: int


# --------------------------------------------------------------------------- SQL text


def _literal(value: object) -> str:
    """A value as an SQL literal. Line breaks become char(10)/char(13), so that
    every row stays on one line of the file."""
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value).replace("'", "''")
    if "\n" not in text and "\r" not in text:
        return f"'{text}'"
    parts, current = [], ""
    for ch in text:
        if ch in "\r\n":
            parts += [f"'{current}'", f"char({ord(ch)})"]
            current = ""
        else:
            current += ch
    parts.append(f"'{current}'")
    return " || ".join(parts)


def dump_table(conn: sqlite3.Connection, table: str) -> str:
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    col_list = ", ".join(columns)
    lines = [HEADER.format(table=table)]
    for row in conn.execute(f"SELECT {col_list} FROM {table} ORDER BY id"):
        lines.append(
            f"INSERT INTO {table} ({col_list}) VALUES ({', '.join(_literal(v) for v in row)});\n"
        )
    return "".join(lines)


def dump_texts(conn: sqlite3.Connection) -> dict[str, str]:
    """{file name: content} exactly as `dump` writes them."""
    return {f"{table}.sql": dump_table(conn, table) for table in TABLES}


def read_texts(data_dir: Path) -> dict[str, str]:
    return {
        f"{t}.sql": (data_dir / f"{t}.sql").read_text(encoding="utf-8")
        for t in TABLES
        if (data_dir / f"{t}.sql").exists()
    }


def write_texts(texts: dict[str, str], data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        # Always LF line endings, also on Windows, so the files are identical everywhere.
        (data_dir / name).write_text(text, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- helpers


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection, paths: Paths) -> None:
    conn.executescript(paths.schema.read_text(encoding="utf-8"))


def broken_references(conn: sqlite3.Connection) -> list[str]:
    return [
        f"{table} row {rowid} refers to a {parent} that does not exist"
        for table, rowid, parent, _ in conn.execute("PRAGMA foreign_key_check").fetchall()
    ]


def counts(conn: sqlite3.Connection) -> Counts:
    return Counts(
        entries=conn.execute("SELECT COUNT(*) FROM entry").fetchone()[0],
        terms=dict(conn.execute("SELECT lang, COUNT(*) FROM term GROUP BY lang").fetchall()),
        definitions=conn.execute("SELECT COUNT(*) FROM definition").fetchone()[0],
    )


def _hashes(texts: dict[str, str]) -> dict[str, str]:
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in texts.items()}


def _changed(old: dict[str, str], new: dict[str, str]) -> list[str]:
    return sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))


def _fingerprint_path(database: Path) -> Path:
    return database.with_name(database.name + ".json")


def _read_fingerprint(database: Path) -> dict | None:
    try:
        fingerprint = json.loads(_fingerprint_path(database).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return fingerprint if {"data", "db"} <= fingerprint.keys() else None


def _write_fingerprint(database: Path, data: dict[str, str], db: dict[str, str]) -> None:
    """Remember the data files the database came from ("data") and what the
    database itself contained at that moment ("db")."""
    _fingerprint_path(database).write_text(
        json.dumps({"data": data, "db": db}, sort_keys=True, indent=1), encoding="utf-8"
    )


def unsaved_edits(database: Path) -> list[str]:
    """Tables edited in the database since it was built or last dumped."""
    fingerprint = _read_fingerprint(database)
    if not database.exists() or fingerprint is None:
        return []
    conn = sqlite3.connect(database)
    try:
        return _changed(fingerprint["db"], _hashes(dump_texts(conn)))
    except sqlite3.DatabaseError:
        return []  # not a TermQuake database (e.g. an older schema): nothing to protect
    finally:
        conn.close()


# --------------------------------------------------------------------------- commands


def load(conn: sqlite3.Connection, data_dir: Path) -> None:
    """Fill a database that has the schema but no rows from data_dir/<table>.sql."""
    missing = [t for t in TABLES if not (data_dir / f"{t}.sql").exists()]
    if missing:
        raise DatabaseError(
            f"{data_dir} has no {', '.join(m + '.sql' for m in missing)}. "
            "Run `termquake import-sheet` once to create the data from the sheet snapshot."
        )
    for table in TABLES:
        sql = (data_dir / f"{table}.sql").read_text(encoding="utf-8")
        try:
            conn.executescript(f"BEGIN;\n{sql}\nCOMMIT;")
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.rollback()
            raise DatabaseError(f"data/db/{table}.sql: {exc}") from exc


def build_database(paths: Paths, *, force: bool = False) -> Counts:
    """data/db/*.sql -> build/termquake.db (replaced as a whole)."""
    out = paths.database
    if not force and (unsaved := unsaved_edits(out)):
        raise DatabaseError(
            f"build/termquake.db has edits that are not saved to data/db/ ({', '.join(unsaved)}). "
            "Run `termquake dump` to save them first, or `termquake build --force` to discard them."
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = connect(tmp)
    try:
        create_schema(conn, paths)
        load(conn, paths.data_db)
        if problems := broken_references(conn):
            raise DatabaseError("broken references in data/db: " + "; ".join(problems[:5]))
        result = counts(conn)
        db_hashes = _hashes(dump_texts(conn))
    finally:
        conn.close()
    tmp.replace(out)
    _write_fingerprint(out, _hashes(read_texts(paths.data_db)), db_hashes)
    return result


def dump_database(paths: Paths, *, check: bool = False, force: bool = False) -> list[str]:
    """build/termquake.db -> data/db/*.sql.

    With check=True nothing is written: returns the files that are not exactly
    what dump would write (CI uses this to prove the committed files are canonical).
    """
    if not paths.database.exists():
        raise DatabaseError("build/termquake.db not found. Run `termquake build` first.")
    conn = connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise DatabaseError(
                "build/termquake.db has an older schema. Run `termquake build --force`."
            )
        texts = dump_texts(conn)
        if check:
            on_disk = read_texts(paths.data_db)
            return [name for name, text in texts.items() if on_disk.get(name) != text]
        fingerprint = _read_fingerprint(paths.database)
        on_disk = _hashes(read_texts(paths.data_db))
        if (
            not force
            and fingerprint is not None
            and (changed := _changed(fingerprint["data"], on_disk))
        ):
            raise DatabaseError(
                f"data/db/ changed after build/termquake.db was built ({', '.join(changed)}), "
                "for example by a git pull or a hand edit. Saving now would undo those changes. "
                "Run `termquake build` to load them, then redo your edit "
                "(or `termquake dump --force` to overwrite them on purpose)."
            )
        if problems := broken_references(conn):
            raise DatabaseError(
                "the database has broken references, so it was not saved: "
                + "; ".join(problems[:5])
            )
    finally:
        conn.close()
    write_texts(texts, paths.data_db)
    _write_fingerprint(paths.database, _hashes(texts), _hashes(texts))  # now identical
    return []


def data_digest(data_dir: Path) -> str:
    """Short fingerprint of the data: changes exactly when the terminology changes."""
    h = hashlib.sha256()
    for name, text in sorted(read_texts(data_dir).items()):
        h.update(name.encode() + b"\0" + text.encode("utf-8") + b"\0")
    return h.hexdigest()[:12]
