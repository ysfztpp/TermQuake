"""Command line: `termquake sync | build | export | all`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import BuildError, build_database
from .config import Paths, find_root, load_config
from .export import export_all
from .fetch import sync


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="termquake", description=__doc__)
    parser.add_argument(
        "command",
        choices=["sync", "build", "export", "all"],
        help="sync: sheet -> data/raw | build: data/raw -> SQLite | "
        "export: SQLite -> exports, downloads, web data | all: build + export",
    )
    parser.add_argument(
        "--raw-dir", type=Path, help="read the snapshot from here instead of data/raw"
    )
    parser.add_argument("--root", type=Path, help="repository root (default: found from cwd)")
    args = parser.parse_args(argv)

    paths = Paths((args.root or find_root()).resolve())
    config = load_config(paths.root / "termquake.toml")
    raw_dir = (args.raw_dir or paths.raw).resolve()

    try:
        if args.command == "sync":
            changed = sync(config, raw_dir)
            print("changed: " + ", ".join(changed) if changed else "no changes in the sheet")
        if args.command in ("build", "all"):
            stats = build_database(config, paths, raw_dir=raw_dir)
            terms = ", ".join(f"{k}={v}" for k, v in stats.terms.items())
            print(
                f"built {paths.database.relative_to(paths.root)}: {stats.concepts} entries, "
                f"terms {terms}, {stats.definitions} definitions, "
                f"{sum(stats.issues.values())} QA issues"
            )
        if args.command in ("export", "all"):
            export_all(config, paths, raw_dir=raw_dir)
            print("exported data/export/, site/public/data/, site/public/downloads/")
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
