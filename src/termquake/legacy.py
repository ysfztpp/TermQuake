"""One-time migration: legacy Google Sheet snapshot -> the SQL database.

The sheet was the project's database until October 2026. It was downloaded
once (read-only) into data/legacy/; this module turns that frozen snapshot
into the SQL database (data/db/*.sql). After the migration the database is the
source of truth and the sheet is no longer used.

The import is conservative (docs/adr/0004): it splits only the unambiguous
synonym separator ("/" with a space), repairs only encoding damage, and keeps
everything else verbatim. Content questions (ambiguous slashes, brackets,
duplicates) are flagged by the regular QA checks after the migration.
Problems that only exist in the sheet (placeholder cells, rows without a
number) are written to data/legacy/MIGRATION_REPORT.md.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .config import Config
from .parse import Issue, parse_cell
from .textnorm import clean, fold

_LANG_IN_HEADER = re.compile(r"\(([A-Za-z][A-Za-z\- ]*)\)")
LEGACY_BOT_ID = 1  # contributor row created by db/seed.sql


class MigrationError(RuntimeError):
    """The legacy snapshot cannot be imported safely (layout changed, missing columns...)."""


@dataclass
class MigrationStats:
    concepts: int = 0
    terms: dict[str, int] = field(default_factory=dict)
    definitions: int = 0
    log: list[tuple[str, str, str]] = field(default_factory=list)  # (where, lang, issue)

    def note(self, where: str, issue: Issue, lang: str | None = None) -> None:
        self.log.append((where, lang or "", f"{issue.severity}: {issue.code}: {issue.detail}"))


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def snapshot_digest(directory: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(directory.glob("*.csv")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


@dataclass
class ColumnMap:
    nr: int
    domain: int
    languages: dict[str, int]  # code -> column index
    unknown: list[str]


def map_columns(header: list[str], config: Config) -> ColumnMap:
    """Find the Nr., Domain and language columns. Languages are matched on the
    English name in parentheses ("Türkçe (Turkish)"), because several native
    names in the sheet headers are misspelled."""
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
        raise MigrationError("Header row must contain 'Nr.' and 'Domain' columns.")
    missing = [code for code in config.languages if code not in languages]
    if missing:
        raise MigrationError(f"Published languages {missing} have no column in the sheet header.")
    return ColumnMap(nr, domain, languages, unknown)


def find_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows):
        if row and clean(row[0])[0] == "Nr.":
            return i
    raise MigrationError("Could not find the header row (a row whose first cell is 'Nr.').")


class Migrator:
    def __init__(self, conn: sqlite3.Connection, config: Config):
        self.conn = conn
        self.config = config
        self.stats = MigrationStats()
        self.domain_ids = {code: did for did, code in conn.execute("SELECT id, code FROM domain")}
        self.source_ids = {
            name: sid for sid, name in conn.execute("SELECT id, short_name FROM source")
        }

    def source_id(self, name: str) -> int | None:
        name = clean(name)[0]
        if not name:
            return None
        if name not in self.source_ids:
            cur = self.conn.execute("INSERT INTO source(short_name) VALUES (?)", (name,))
            self.source_ids[name] = cur.lastrowid
        return self.source_ids[name]

    def load_terms(self, rows: list[list[str]]) -> None:
        h = find_header(rows)
        header = rows[h]
        cols = map_columns(header, self.config)
        for name in cols.unknown:
            self.stats.note(
                f"header row {h + 1}", Issue("info", "unknown_column", f"{name!r} not mapped")
            )
        seen: set[int] = set()
        for line_no, row in enumerate(rows[h + 1 :], start=h + 2):
            row = row + [""] * (len(header) - len(row))
            if not any(cell.strip() for cell in row):
                continue
            nr_text = clean(row[cols.nr])[0]
            if not nr_text.isdigit():
                self.stats.note(
                    f"row {line_no}",
                    Issue(
                        "error", "missing_nr", "row has content but no numeric Nr.; not imported"
                    ),
                )
                continue
            nr = int(nr_text)
            if nr in seen:
                self.stats.note(
                    f"row {line_no}",
                    Issue(
                        "error", "duplicate_nr", f"Nr. {nr} used twice; this row was not imported"
                    ),
                )
                continue
            seen.add(nr)
            self._load_concept(nr, row, cols)

    def _load_concept(self, nr: int, row: list[str], cols: ColumnMap) -> None:
        label = clean(row[cols.domain])[0]
        is_phrase = label in self.config.phrase_labels
        domain_id = None
        if not is_phrase and label:
            code = self.config.domains.get(label)
            if code:
                domain_id = self.domain_ids[code]
            else:
                self.stats.note(
                    f"entry {nr}", Issue("warning", "unknown_domain", f"{label!r}; left empty")
                )
        self.conn.execute(
            "INSERT INTO concept(id, legacy_nr, domain_id, entry_type) VALUES (?,?,?,?)",
            (nr, nr, domain_id, "phrase" if is_phrase else "term"),
        )
        self.stats.concepts += 1

        for lang, col in cols.languages.items():
            parsed = parse_cell(row[col], is_phrase=is_phrase)
            for issue in parsed.issues:  # cell-level: placeholders, repairs, duplicates in a cell
                self.stats.note(f"entry {nr}", issue, lang)
            for order, term in enumerate(parsed.terms):
                self.conn.execute(
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

    def load_definitions(self, rows: list[list[str]]) -> None:
        h = next(
            (i for i, r in enumerate(rows) if len(r) > 1 and clean(r[1])[0] == "English"), None
        )
        if h is None:
            raise MigrationError("definitions tab: header row with 'English' in column B not found")
        header = [clean(c)[0].lower() for c in rows[h]]
        layout = {"en": (4, None), "tr": (8, 9)}  # lang -> (definition column, source column)
        for dcol, _ in layout.values():
            if len(header) <= dcol or not header[dcol].startswith("defini"):
                raise MigrationError(
                    f"definitions tab: column {dcol + 1} is not a definition column"
                )
        known = {cid for (cid,) in self.conn.execute("SELECT id FROM concept")}
        for line_no, row in enumerate(rows[h + 1 :], start=h + 2):
            row = row + [""] * (len(header) - len(row))
            nr_text = clean(row[0])[0]
            if not nr_text.isdigit():
                continue
            nr = int(nr_text)
            for lang, (dcol, scol) in layout.items():
                text = clean(row[dcol])[0]
                if not text:
                    continue
                if nr not in known:
                    self.stats.note(
                        f"definitions row {line_no}",
                        Issue(
                            "warning",
                            "definition_unknown_entry",
                            f"Nr. {nr} does not exist; not imported",
                        ),
                        lang,
                    )
                    continue
                source = self.source_id(row[scol]) if scol is not None else None
                self.conn.execute(
                    "INSERT INTO definition(concept_id, lang, text, source_id, origin, updated_by) "
                    "VALUES (?,?,?,?,?,?)",
                    (nr, lang, text, source, "legacy_import", LEGACY_BOT_ID),
                )
                self.stats.definitions += 1


def migrate_into(
    conn: sqlite3.Connection, config: Config, legacy_dir: Path, seed_sql: str
) -> MigrationStats:
    """Fill an empty database (schema already created) from the legacy snapshot."""
    terms_csv = legacy_dir / "terms.csv"
    if not terms_csv.exists():
        raise MigrationError(f"{terms_csv} not found.")
    conn.executescript(seed_sql)
    conn.execute(
        "INSERT INTO import_batch(source_url, script_version, notes) VALUES (?,?,?)",
        (
            config.legacy_sheet_url,
            __version__,
            f"one-time migration from the legacy Google Sheet snapshot {snapshot_digest(legacy_dir)}",
        ),
    )
    migrator = Migrator(conn, config)
    migrator.load_terms(read_csv(terms_csv))
    if (legacy_dir / "definitions.csv").exists():
        migrator.load_definitions(read_csv(legacy_dir / "definitions.csv"))
    return migrator.stats


def write_migration_report(stats: MigrationStats, path: Path) -> None:
    lines = [
        "# Migration report: legacy Google Sheet -> SQL database",
        "",
        "Written once by `termquake migrate`. Lists what the legacy sheet contained that",
        "could not be imported as-is. Content questions (ambiguous separators, duplicates,",
        "missing translations) are tracked in data/QA_REPORT.md instead.",
        "",
        f"- Entries imported: {stats.concepts}",
        f"- Terms imported: {sum(stats.terms.values())} "
        f"({', '.join(f'{k} {v}' for k, v in sorted(stats.terms.items()))})",
        f"- Definitions imported: {stats.definitions}",
        "",
        "| Where | Language | Finding |",
        "|---|---|---|",
    ]
    for where, lang, text in stats.log:
        lines.append(f"| {where} | {lang} | {text.replace('|', chr(92) + '|')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
