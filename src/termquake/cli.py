"""termquake: build, edit and publish the TermQuake database.

Everyday work:
  termquake build          data/db/*.sql -> build/termquake.db
  (edit build/termquake.db with SQL, DB Browser for SQLite or a script)
  termquake dump           build/termquake.db -> data/db/*.sql; then review with git diff and commit
  termquake export         build/termquake.db -> downloads and website data
  termquake all            build + export

Rare:
  termquake import-sheet   create data/db from the sheet snapshot in data/legacy (already done)
  termquake fetch-sheet    download a Google Sheet (e.g. a copy) as CSV, read-only
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from .config import Config, Paths, find_root, load_config
from .db import (
    DatabaseError,
    build_database,
    connect,
    create_schema,
    dump_database,
    dump_texts,
    write_texts,
)
from .export import ExportError, export_all
from .fetch import fetch_sheet
from .sheet import SheetError, import_sheet, write_report


def run_import(config: Config, paths: Paths, *, force: bool) -> str:
    if any(paths.data_db.glob("*.sql")) and not force:
        raise SheetError(
            "data/db already exists, and it is the source of truth now. Importing again "
            "would overwrite every edit made since. Use --force only to start over from the sheet."
        )
    conn = connect(":memory:")
    try:
        create_schema(conn, paths)
        stats = import_sheet(conn, config, paths.legacy)
        conn.commit()
        texts = dump_texts(conn)
    finally:
        conn.close()
    for old in paths.data_db.glob("*.sql"):
        old.unlink()
    write_texts(texts, paths.data_db)
    write_report(stats, paths.legacy / "IMPORT_REPORT.md")
    build_database(paths, force=True)
    per_lang = ", ".join(f"{k} {v}" for k, v in stats.terms.items())
    return (
        f"imported {stats.entries} entries, {sum(stats.terms.values())} terms ({per_lang}), "
        f"{stats.definitions} definitions -> data/db/ (see data/legacy/IMPORT_REPORT.md)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="termquake", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, help="repository root (default: found from cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build the database from data/db")
    build.add_argument("--force", action="store_true", help="discard edits that were not dumped")
    dump = sub.add_parser("dump", help="save the database to data/db")
    dump.add_argument(
        "--check", action="store_true", help="write nothing; fail if data/db is not canonical"
    )
    dump.add_argument(
        "--force", action="store_true", help="save even if data/db changed since the build"
    )
    sub.add_parser("export", help="write the downloads and the website data")
    sub.add_parser("all", help="build + export")
    imp = sub.add_parser("import-sheet", help="create data/db from the sheet snapshot (once)")
    imp.add_argument("--force", action="store_true", help="overwrite an existing data/db")
    fetch = sub.add_parser("fetch-sheet", help="download a Google Sheet's tabs as CSV (read-only)")
    fetch.add_argument("--sheet-id", required=True, help="ID of the sheet to read (use a copy)")
    fetch.add_argument("--out", type=Path, required=True, help="directory for the CSV files")
    args = parser.parse_args(argv)

    paths = Paths((args.root or find_root()).resolve())
    config = load_config(paths.root / "termquake.toml")
    try:
        if args.command == "import-sheet":
            print(run_import(config, paths, force=args.force))
        if args.command in ("build", "all"):
            c = build_database(paths, force=getattr(args, "force", False))
            terms = ", ".join(f"{lang} {c.terms.get(lang, 0)}" for lang in config.languages)
            print(
                f"built build/termquake.db: {c.entries} entries, terms: {terms}, "
                f"{c.definitions} definitions"
            )
        if args.command in ("export", "all"):
            export_all(config, paths)
            print("exported site/public/data/termbase.json and site/public/downloads/")
        if args.command == "dump":
            stale = dump_database(paths, check=args.check, force=args.force)
            if args.check:
                if stale:
                    print(
                        f"not in canonical form: {', '.join(stale)}\n"
                        "Run `termquake build && termquake dump` and commit the result.",
                        file=sys.stderr,
                    )
                    return 1
                print("data/db is in canonical form")
            else:
                print("saved data/db/; review with `git diff data/db`, then commit")
        if args.command == "fetch-sheet":
            changed = fetch_sheet(args.sheet_id, config.tabs, args.out)
            print("changed: " + ", ".join(changed) if changed else "no changes")
    except (DatabaseError, SheetError, ExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
