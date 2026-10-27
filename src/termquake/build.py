"""Build the SQLite termbase from the raw sheet snapshot.

The database is a build artifact: it is recreated from data/raw on every
run, so the build is reproducible and the schema can evolve freely while the
Google Sheet is still the place where people edit. (In phase 2 the database
becomes the source of truth and this importer runs once as a migration.)
"""

from __future__ import annotations

import csv
import os
import re
import sqlite3
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .config import Config, Paths
from .fetch import snapshot_digest
from .parse import Issue, parse_cell
from .textnorm import clean, fold

_LANG_IN_HEADER = re.compile(r"\(([A-Za-z][A-Za-z\- ]*)\)")
LEGACY_BOT_ID = 1  # contributor row created by db/seed.sql


class BuildError(RuntimeError):
    """The raw data cannot be imported safely (layout changed, missing columns...)."""


@dataclass
class BuildStats:
    concepts: int = 0
    terms: dict[str, int] = field(default_factory=dict)
    definitions: int = 0
    issues: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def _git_commit(root: Path) -> str:
    if sha := os.environ.get("GITHUB_SHA"):
        return sha[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass
class ColumnMap:
    nr: int
    domain: int
    languages: dict[str, int]  # code -> column index
    unknown: list[str]


def map_columns(header: list[str], config: Config) -> ColumnMap:
    nr = domain = None
    languages: dict[str, int] = {}
    unknown: list[str] = []
    for idx, raw in enumerate(header):
        name = clean(raw)[0]
        if not name:
            continue
        if name == "Nr.":
            nr = idx
        elif name == "Domain":
            domain = idx
        else:
            key = name if name in config.columns else None
            if key is None and (m := _LANG_IN_HEADER.search(name)):
                key = m.group(1).strip()
            code = config.columns.get(key) if key else None
            if code:
                languages[code] = idx
            else:
                unknown.append(name)
    if nr is None or domain is None:
        raise BuildError("Header row must contain 'Nr.' and 'Domain' columns.")
    missing = [code for code in config.languages if code not in languages]
    if missing:
        raise BuildError(f"Published languages {missing} have no column in the sheet header.")
    return ColumnMap(nr, domain, languages, unknown)


def find_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows):
        if row and clean(row[0])[0] == "Nr.":
            return i
    raise BuildError("Could not find the header row (a row whose first cell is 'Nr.').")


# --------------------------------------------------------------------------- builder


class Builder:
    def __init__(self, conn: sqlite3.Connection, config: Config):
        self.conn = conn
        self.config = config
        self.stats = BuildStats()
        self.domain_ids = {code: did for did, code in conn.execute("SELECT id, code FROM domain")}
        self.source_ids = {
            name: sid for sid, name in conn.execute("SELECT id, short_name FROM source")
        }

    # ---- issues
    def issue(
        self, entity_type: str, entity_id: int, issue: Issue, lang: str | None = None
    ) -> None:
        self.conn.execute(
            "INSERT INTO qa_issue(entity_type, entity_id, severity, issue_type, lang, detail) "
            "VALUES (?,?,?,?,?,?)",
            (entity_type, entity_id, issue.severity, issue.code, lang, issue.detail),
        )
        self.stats.issues[issue.code] = self.stats.issues.get(issue.code, 0) + 1

    def source_id(self, name: str) -> int | None:
        name = clean(name)[0]
        if not name:
            return None
        if name not in self.source_ids:
            cur = self.conn.execute("INSERT INTO source(short_name) VALUES (?)", (name,))
            self.source_ids[name] = cur.lastrowid
        return self.source_ids[name]

    # ---- terms tab
    def load_terms(self, rows: list[list[str]], batch_id: int) -> None:
        h = find_header(rows)
        header = rows[h]
        cols = map_columns(header, self.config)
        for name in cols.unknown:
            self.issue("row", h + 1, Issue("info", "unknown_column", f"header {name!r} not mapped"))

        published = [c for c in self.config.languages]
        seen_nr: set[int] = set()
        for line_no, row in enumerate(rows[h + 1 :], start=h + 2):
            row = row + [""] * (len(header) - len(row))
            if not any(cell.strip() for cell in row):
                continue
            nr_text = clean(row[cols.nr])[0]
            if not nr_text.isdigit():
                self.issue(
                    "row",
                    line_no,
                    Issue(
                        "error",
                        "missing_nr",
                        f"row {line_no} has content but no numeric Nr.; skipped",
                    ),
                )
                continue
            nr = int(nr_text)
            if nr in seen_nr:
                self.issue(
                    "row",
                    line_no,
                    Issue("error", "duplicate_nr", f"Nr. {nr} used twice; row {line_no} skipped"),
                )
                continue
            seen_nr.add(nr)
            self._load_concept(nr, row, header, cols, published, batch_id, line_no)

        self._flag_duplicates()

    def _load_concept(self, nr, row, header, cols, published, batch_id, line_no) -> None:
        label = clean(row[cols.domain])[0]
        is_phrase = label in self.config.phrase_labels
        domain_id = None
        pending: list[Issue] = []
        if not is_phrase:
            code = self.config.domains.get(label)
            if code:
                domain_id = self.domain_ids[code]
            elif label:
                pending.append(Issue("warning", "unknown_domain", f"domain label {label!r}"))
            else:
                pending.append(Issue("warning", "missing_domain", "domain cell is empty"))

        self.conn.execute(
            "INSERT INTO concept(id, legacy_nr, domain_id, entry_type) VALUES (?,?,?,?)",
            (nr, nr, domain_id, "phrase" if is_phrase else "term"),
        )
        self.stats.concepts += 1
        for issue in pending:
            self.issue("concept", nr, issue)

        # Lossless archive of every non-empty cell, all languages.
        self.conn.executemany(
            "INSERT INTO import_raw(batch_id, sheet, row_number, column_name, raw_value, concept_id) "
            "VALUES (?,?,?,?,?,?)",
            [
                (batch_id, "terms", line_no, clean(header[i])[0] or f"col{i}", value, nr)
                for i, value in enumerate(row)
                if value.strip()
            ],
        )

        for lang in published:
            parsed = parse_cell(row[cols.languages[lang]], is_phrase=is_phrase)
            for issue in parsed.issues:
                self.issue("concept", nr, issue, lang)
            for order, term in enumerate(parsed.terms):
                cur = self.conn.execute(
                    "INSERT INTO term(concept_id, lang, text, text_norm, sort_order, term_type, "
                    "origin, source_id, created_by, updated_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        nr,
                        lang,
                        term.text,
                        fold(term.text),
                        order,
                        "phrase" if is_phrase else None,
                        "legacy_import",
                        self.source_ids.get("TQ-SHEET"),
                        LEGACY_BOT_ID,
                        LEGACY_BOT_ID,
                    ),
                )
                self.stats.terms[lang] = self.stats.terms.get(lang, 0) + 1
                for issue in term.issues:
                    self.issue("term", cur.lastrowid, issue, lang)
            if not parsed.terms and lang == self.config.pivot:
                self.issue(
                    "concept",
                    nr,
                    Issue(
                        "warning",
                        "missing_pivot_term",
                        f"no {lang} term; the entry cannot be looked up from {lang}",
                    ),
                    lang,
                )

    def _flag_duplicates(self) -> None:
        dupes = self.conn.execute(
            "SELECT lang, text_norm, group_concat(DISTINCT concept_id) FROM term "
            "GROUP BY lang, text_norm HAVING COUNT(DISTINCT concept_id) > 1"
        ).fetchall()
        for lang, norm, concept_list in dupes:
            ids = sorted(int(x) for x in concept_list.split(","))
            for term_id, concept_id, text in self.conn.execute(
                "SELECT id, concept_id, text FROM term WHERE lang=? AND text_norm=?", (lang, norm)
            ).fetchall():
                others = ", ".join(str(i) for i in ids if i != concept_id)
                # In the pivot language a repeated term usually means a duplicated row.
                # In target languages one word legitimately translates related concepts.
                severity = "warning" if lang == self.config.pivot else "info"
                self.issue(
                    "term",
                    term_id,
                    Issue(
                        severity,
                        "duplicate_term",
                        f"{text!r} also appears in entry {others} (possible duplicate entry)",
                    ),
                    lang,
                )

    # ---- definitions tab
    def load_definitions(self, rows: list[list[str]]) -> None:
        h = next(
            (i for i, r in enumerate(rows) if len(r) > 1 and clean(r[1])[0] == "English"), None
        )
        if h is None:
            raise BuildError("definitions tab: header row with 'English' in column B not found")
        header = [clean(c)[0].lower() for c in rows[h]]
        layout = {"en": (4, None), "tr": (8, 9)}  # lang -> (definition col, source col)
        for dcol, _ in layout.values():
            if len(header) <= dcol or not header[dcol].startswith("defini"):
                raise BuildError(
                    f"definitions tab: column {dcol + 1} is no longer a definition column"
                )
        known = {cid for (cid,) in self.conn.execute("SELECT id FROM concept")}
        for line_no, row in enumerate(rows[h + 1 :], start=h + 2):
            row = row + [""] * (len(header) - len(row))
            nr_text = clean(row[0])[0]
            if not nr_text.isdigit():
                continue
            nr = int(nr_text)
            for lang, (dcol, scol) in layout.items():
                if lang not in self.config.languages:
                    continue
                text = clean(row[dcol])[0]
                if not text:
                    continue
                if nr not in known:
                    self.issue(
                        "row",
                        line_no,
                        Issue(
                            "warning",
                            "definition_unknown_entry",
                            f"definition for Nr. {nr} but no such entry",
                        ),
                        lang,
                    )
                    continue
                source = self.source_id(row[scol]) if scol is not None else None
                cur = self.conn.execute(
                    "INSERT INTO definition(concept_id, lang, text, source_id, origin, updated_by) "
                    "VALUES (?,?,?,?,?,?)",
                    (nr, lang, text, source, "legacy_import", LEGACY_BOT_ID),
                )
                self.stats.definitions += 1
                for issue in _definition_issues(text):
                    self.issue("definition", cur.lastrowid, issue, lang)


def _definition_issues(text: str) -> Iterable[Issue]:
    if "?" in text:
        yield Issue(
            "warning",
            "definition_needs_review",
            f"{text[:80]!r}: contains a question; looks like a discussion note",
        )
    if len(text) < 15:
        yield Issue("warning", "definition_too_short", f"{text!r}")


# --------------------------------------------------------------------------- entry point


def build_database(
    config: Config, paths: Paths, raw_dir: Path | None = None, out: Path | None = None
) -> BuildStats:
    raw_dir = raw_dir or paths.raw
    out = out or paths.database
    terms_csv = raw_dir / "terms.csv"
    if not terms_csv.exists():
        raise BuildError(f"{terms_csv} not found. Run `termquake sync` first.")

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((paths.db_dir / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((paths.db_dir / "seed.sql").read_text(encoding="utf-8"))
        conn.execute("UPDATE language SET is_active = 0")
        conn.executemany(
            "UPDATE language SET is_active = 1 WHERE code = ?", [(c,) for c in config.languages]
        )

        digest = snapshot_digest(raw_dir)
        batch_id = conn.execute(
            "INSERT INTO import_batch(source_url, script_version, notes) VALUES (?,?,?)",
            (
                config.sheet_url,
                f"{__version__}+{_git_commit(paths.root)}",
                f"raw snapshot {digest}",
            ),
        ).lastrowid

        builder = Builder(conn, config)
        builder.load_terms(read_csv(terms_csv), batch_id)
        definitions_csv = raw_dir / "definitions.csv"
        if definitions_csv.exists():
            builder.load_definitions(read_csv(definitions_csv))

        # History starts now: from here on, every change is recorded.
        conn.executescript((paths.db_dir / "triggers.sql").read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise BuildError(f"foreign key violations: {problems[:5]}")
        conn.execute("ANALYZE")
        conn.commit()
    finally:
        conn.close()
    tmp.replace(out)
    return builder.stats
