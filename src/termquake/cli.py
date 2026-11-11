"""termquake: build, edit and publish the TermQuake database.

Everyday work:
  termquake build          data/db/*.sql -> build/termquake.db
  (edit build/termquake.db with SQL, DB Browser for SQLite or a script)
  termquake dump           build/termquake.db -> data/db/*.sql; then review with git diff and commit
  termquake export         build/termquake.db -> downloads and website data
  termquake all            build + export
  termquake clean          fix spaces, invisible characters and Unicode form in build/termquake.db
  termquake review en      write the review sheet for one language (data/review/)

Rare:
  termquake import-sheet   create data/db from the sheet snapshot in data/legacy (already done)
  termquake fetch-sheet    download a Google Sheet (e.g. a copy) as CSV, read-only
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from .ai import import_ai
from .clean import RULES, clean_database
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
from .review import build_review, read_suggestions, write_review_xlsx
from .sheet import SheetError, import_sheet, write_report
from .standardise import standardise


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
    return (
        f"imported {stats.entries} entries, "
        f"{sum(stats.terms.values())} terms in {len(stats.terms)} languages, "
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
    clean = sub.add_parser(
        "clean", help="mechanical clean-up of build/termquake.db (spaces, invisible characters)"
    )
    clean.add_argument(
        "--check", action="store_true", help="change nothing; fail if a text needs cleaning"
    )
    sub.add_parser("all", help="build + export")
    imp = sub.add_parser("import-sheet", help="create data/db from the sheet snapshot (once)")
    imp.add_argument("--force", action="store_true", help="overwrite an existing data/db")
    review = sub.add_parser("review", help="write the review sheet (xlsx) for one language")
    review.add_argument("lang", help="language code, e.g. en")
    review.add_argument("--out", type=Path, help="output file (default: build/review-<lang>.xlsx)")
    sub.add_parser("standardise", help="split cells into one row per term (build/termquake.db)")
    sub.add_parser("ai-import", help="fill gaps from data/ai/ (terms, definitions), marked as AI")
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
            print(
                f"built build/termquake.db: {c.entries} entries, "
                f"{sum(c.terms.values())} terms in {len(c.terms)} languages, "
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
        if args.command == "clean":
            if not paths.database.exists():
                raise DatabaseError("build/termquake.db not found. Run `termquake build` first.")
            conn = connect(paths.database)
            try:
                stats = clean_database(conn, apply=not args.check)
            finally:
                conn.close()
            total = sum(stats.changed.values())
            by_rule = ", ".join(f"{r} {stats.rules[r]}" for r in RULES if stats.rules[r])
            if args.check:
                if total:
                    print(
                        f"{total} texts need cleaning ({by_rule}).\n"
                        "Run `termquake build && termquake clean && termquake dump` and commit.",
                        file=sys.stderr,
                    )
                    return 1
                print("all texts are clean")
            elif total:
                print(f"cleaned {total} texts ({by_rule}); run `termquake dump` to save")
            else:
                print("nothing to clean")
        if args.command == "review":
            if not paths.database.exists():
                raise DatabaseError("build/termquake.db not found. Run `termquake build` first.")
            conn = connect(paths.database)
            try:
                name = conn.execute(
                    "SELECT name_en FROM language WHERE code = ?", (args.lang,)
                ).fetchone()
                if name is None:
                    raise DatabaseError(f"no language with code {args.lang!r}")
                suggestions = read_suggestions(
                    paths.root / "data" / "review" / f"{args.lang}.suggestions.csv"
                )
                rows = build_review(conn, args.lang, suggestions)
            finally:
                conn.close()
            counts: dict[str, int] = {}
            for r in rows:
                for rule in r.rules:
                    counts[rule] = counts.get(rule, 0) + 1
            out = args.out or paths.build / f"review-{args.lang}.xlsx"
            write_review_xlsx(rows, name[0], out, counts)
            need = sum(1 for r in rows if r.status == "review")
            print(f"wrote {out}: {len(rows)} rows, {need} need a decision")
        if args.command in ("standardise", "ai-import"):
            if not paths.database.exists():
                raise DatabaseError("build/termquake.db not found. Run `termquake build` first.")
            conn = connect(paths.database)
            try:
                if args.command == "standardise":
                    changed = standardise(conn, paths.root / "data" / "review")
                    print(f"standardised {sum(changed.values())} cells in {len(changed)} languages")
                else:
                    terms, defs = import_ai(conn, paths.root / "data" / "ai")
                    print(
                        f"added {sum(terms.values())} AI terms in {len(terms)} languages, "
                        f"{sum(defs.values())} AI definitions; run `termquake dump` to save"
                    )
            finally:
                conn.close()
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
