"""termquake: build, edit and publish the TermQuake SQL database.

Everyday work:
  termquake build          data/db/*.sql -> build/termquake.db (+ QA checks)
  (edit build/termquake.db with SQL, a script or a database GUI)
  termquake dump           build/termquake.db -> data/db/*.sql + data/QA_REPORT.md, then commit
  termquake export         build/termquake.db -> downloads and web app data
  termquake all            build + export

One-time / rare:
  termquake migrate        create data/db from the legacy sheet snapshot (already done)
  termquake fetch-sheet    download a Google Sheet (e.g. a copy) as CSV, read-only
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from .build import BuildError, build_database, dump_database, migrate
from .config import Paths, find_root, load_config
from .export import ExportError, export_all
from .fetch import fetch_sheet
from .legacy import MigrationError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="termquake", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, help="repository root (default: found from cwd)")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build the database from data/db")
    build.add_argument(
        "--force", action="store_true", help="discard edits in build/termquake.db not yet dumped"
    )
    dump = sub.add_parser("dump", help="save the database to data/db and refresh the QA report")
    dump.add_argument(
        "--check",
        action="store_true",
        help="write nothing; fail if the committed files are not up to date",
    )
    dump.add_argument(
        "--force", action="store_true", help="save even if data/db changed since the build"
    )
    sub.add_parser("export", help="write downloads and web app data")
    sub.add_parser("all", help="build + export")
    mig = sub.add_parser("migrate", help="one-time: create data/db from data/legacy")
    mig.add_argument("--force", action="store_true", help="overwrite an existing data/db")
    fetch = sub.add_parser("fetch-sheet", help="download a Google Sheet's tabs as CSV (read-only)")
    fetch.add_argument("--sheet-id", required=True, help="ID of the sheet to read (use a copy)")
    fetch.add_argument("--out", type=Path, required=True, help="directory for the CSV files")
    args = parser.parse_args(argv)

    paths = Paths((args.root or find_root()).resolve())
    config = load_config(paths.root / "termquake.toml")

    try:
        if args.command == "migrate":
            stats = migrate(config, paths, force=args.force)
            print(
                f"migrated {stats.concepts} entries, {sum(stats.terms.values())} terms in "
                f"{len(stats.terms)} languages, {stats.definitions} definitions -> data/db/ "
                f"(see data/legacy/MIGRATION_REPORT.md)"
            )
        if args.command in ("build", "all"):
            r = build_database(config, paths, force=getattr(args, "force", False))
            published = ", ".join(f"{lang}={r.terms.get(lang, 0)}" for lang in config.languages)
            print(
                f"built build/termquake.db: {r.concepts} entries, {sum(r.terms.values())} terms "
                f"in {len(r.terms)} languages (published: {published}), {r.definitions} definitions, "
                f"{sum(r.issues.values())} QA findings"
            )
        if args.command in ("export", "all"):
            export_all(config, paths)
            print("exported site/public/data/termbase.json and site/public/downloads/")
        if args.command == "dump":
            result = dump_database(config, paths, check=args.check, force=args.force)
            if args.check:
                if result.stale_files:
                    print(
                        "not in canonical form: "
                        + ", ".join(result.stale_files)
                        + "\nRun `termquake build && termquake dump` and commit the result.",
                        file=sys.stderr,
                    )
                    return 1
                if result.report_stale:
                    # Not a failure: a data edit made on GitHub can't refresh the report.
                    print(
                        "warning: data/QA_REPORT.md is out of date; "
                        "`termquake build && termquake dump` refreshes it",
                        file=sys.stderr,
                    )
                print("data/db is in canonical form")
            else:
                print("saved data/db/ and data/QA_REPORT.md; review with `git diff`, then commit")
        if args.command == "fetch-sheet":
            changed = fetch_sheet(args.sheet_id, config.tabs, args.out)
            print("changed: " + ", ".join(changed) if changed else "no changes")
    except (BuildError, MigrationError, ExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
