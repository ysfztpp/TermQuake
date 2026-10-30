"""Import the original Google Sheet (frozen snapshot in data/legacy/) into the database.

The import keeps the data exactly as typed in the sheet (docs/adr/0010):
every English, Turkish and Spanish cell becomes one `term` row with the cell's
text unchanged, including synonyms written together ("enkaz / moloz"),
spaces and unusual characters. The only cells left out are empty ones and
spreadsheet placeholders such as "#empty1" or "#N/A", which are not terms.

What the import noticed (but did not change) is written to
data/legacy/IMPORT_REPORT.md, as a worklist for the team.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config

# Domain rows: (id, code, English, Turkish, Spanish name). The sheet's "Domain"
# values are mapped to these codes in termquake.toml.
DOMAINS = [
    (1, "general", "General Terms", "Genel Terimler", "Términos generales"),
    (2, "search_rescue", "Search & Rescue", "Arama Kurtarma", "Búsqueda y rescate"),
    (3, "first_aid", "First Aid", "İlk Yardım", "Primeros auxilios"),
    (4, "medical", "Medical Terms", "Tıbbi Terimler", "Términos médicos"),
    (5, "misc", "Miscellaneous", "Diğer", "Varios"),
    (6, "expressions", "Expressions", "İfadeler", "Expresiones"),
]

PLACEHOLDER = re.compile(r"^#(empty\d*|N/A|REF!|VALUE!|NAME\?|DIV/0!|ERROR!?|NULL!)$", re.I)
_INVISIBLE = re.compile("[​‌‍⁠﻿­]")
_LANG_IN_HEADER = re.compile(r"\(([A-Za-z][A-Za-z\- ]*)\)")


class SheetError(RuntimeError):
    """The snapshot cannot be imported (layout changed, columns missing, data already there)."""


@dataclass
class ImportStats:
    entries: int = 0
    terms: dict[str, int] = field(default_factory=dict)
    definitions: int = 0
    skipped: list[tuple[str, str, str]] = field(default_factory=list)  # (where, lang, why)
    notes: dict[str, list[str]] = field(default_factory=dict)  # kind -> ["entry 5 (tr)", ...]

    def note(self, kind: str, where: str) -> None:
        self.notes.setdefault(kind, []).append(where)


def _label(text: str) -> str:
    """A header or domain value for matching only (the data itself is never changed)."""
    return _INVISIBLE.sub("", text).strip()


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def _columns(header: list[str], config: Config) -> tuple[int, int, dict[str, int]]:
    """Positions of the Nr. and Domain columns and of each language's column."""
    nr = domain = None
    langs: dict[str, int] = {}
    for i, raw in enumerate(header):
        name = _label(raw)
        if name == "Nr.":
            nr = i
        elif name == "Domain":
            domain = i
        else:
            key = name if name in config.columns else None
            if key is None and (m := _LANG_IN_HEADER.search(name)):
                key = m.group(1).strip()
            if key in config.columns:
                langs[config.columns[key]] = i
    if nr is None or domain is None:
        raise SheetError("terms tab: the header row needs 'Nr.' and 'Domain' columns")
    if missing := [code for code in config.languages if code not in langs]:
        raise SheetError(f"terms tab: no column for {missing}")
    return nr, domain, langs


def _value(cell: str) -> str | None:
    """The cell's text exactly as typed, or None for an empty cell or a placeholder."""
    if not cell.strip() or PLACEHOLDER.match(cell.strip()):
        return None
    return cell


def _observe(stats: ImportStats, text: str, where: str) -> None:
    """Things worth a look, recorded in the report. Nothing is changed."""
    if text != text.strip():
        stats.note("Space at the start or end of the cell", where)
    if "̇" in text:
        stats.note("Letter i written as i + combining dot (looks like i̇)", where)
    if _INVISIBLE.search(text):
        stats.note("Invisible character in the cell", where)
    if " / " in text:
        stats.note("Several terms in one cell, separated by ' / '", where)


def import_terms(
    conn: sqlite3.Connection, config: Config, rows: list[list[str]], stats: ImportStats
) -> None:
    head = next((i for i, r in enumerate(rows) if r and _label(r[0]) == "Nr."), None)
    if head is None:
        raise SheetError("terms tab: no header row (a row whose first cell is 'Nr.')")
    header = rows[head]
    nr_col, domain_col, lang_cols = _columns(header, config)
    domain_ids = {code: did for did, code, *_ in DOMAINS}
    seen: set[int] = set()
    for line, row in enumerate(rows[head + 1 :], start=head + 2):
        row = row + [""] * (len(header) - len(row))
        if not any(cell.strip() for cell in row):
            continue
        nr_text = _label(row[nr_col])
        if not nr_text.isdigit():
            stats.skipped.append((f"sheet row {line}", "", "no number in the Nr. column"))
            continue
        nr = int(nr_text)
        if nr in seen:
            stats.skipped.append((f"sheet row {line}", "", f"Nr. {nr} is used twice"))
            continue
        seen.add(nr)

        domain_value = _label(row[domain_col])
        domain_id = None
        if domain_value:
            code = config.domains.get(domain_value)
            if code is None:
                stats.skipped.append(
                    (f"entry {nr}", "", f"unknown domain {domain_value!r}; left empty")
                )
            else:
                domain_id = domain_ids[code]
        else:
            stats.note("Entry without a domain", f"entry {nr}")
        conn.execute("INSERT INTO entry(id, domain_id) VALUES (?, ?)", (nr, domain_id))
        stats.entries += 1

        for lang in config.languages:
            cell = row[lang_cols[lang]]
            text = _value(cell)
            if text is None:
                if cell.strip():
                    stats.skipped.append((f"entry {nr}", lang, f"placeholder {cell.strip()!r}"))
                continue
            _observe(stats, text, f"entry {nr} ({lang})")
            conn.execute(
                "INSERT INTO term(entry_id, lang, text) VALUES (?, ?, ?)", (nr, lang, text)
            )
            stats.terms[lang] = stats.terms.get(lang, 0) + 1


def import_definitions(conn: sqlite3.Connection, rows: list[list[str]], stats: ImportStats) -> None:
    """The "Terms Needing Definition Selection" tab: English and Turkish definitions."""
    head = next((i for i, r in enumerate(rows) if len(r) > 1 and _label(r[1]) == "English"), None)
    if head is None:
        raise SheetError("definitions tab: no header row with 'English' in column B")
    header = [_label(c).lower() for c in rows[head]]
    layout = {"en": (4, None), "tr": (8, 9)}  # language -> (definition column, source column)
    for col, _ in layout.values():
        if len(header) <= col or not header[col].startswith("defini"):
            raise SheetError(f"definitions tab: column {col + 1} is not a definition column")
    entries = {eid for (eid,) in conn.execute("SELECT id FROM entry")}
    for line, row in enumerate(rows[head + 1 :], start=head + 2):
        row = row + [""] * (len(header) - len(row))
        nr_text = _label(row[0])
        if not nr_text.isdigit():
            continue
        nr = int(nr_text)
        for lang, (dcol, scol) in layout.items():
            text = _value(row[dcol])
            if text is None:
                continue
            if nr not in entries:
                stats.skipped.append((f"definitions row {line}", lang, f"Nr. {nr} does not exist"))
                continue
            source = row[scol] if scol is not None and row[scol].strip() else None
            conn.execute(
                "INSERT INTO definition(entry_id, lang, text, source) VALUES (?, ?, ?, ?)",
                (nr, lang, text, source),
            )
            stats.definitions += 1


def import_sheet(conn: sqlite3.Connection, config: Config, legacy_dir: Path) -> ImportStats:
    """Fill an empty database (schema already created) from the snapshot."""
    terms_csv = legacy_dir / "terms.csv"
    if not terms_csv.exists():
        raise SheetError(f"{terms_csv} not found")
    stats = ImportStats()
    conn.executemany(
        "INSERT INTO domain(id, code, name_en, name_tr, name_es) VALUES (?, ?, ?, ?, ?)", DOMAINS
    )
    import_terms(conn, config, read_csv(terms_csv), stats)
    if (legacy_dir / "definitions.csv").exists():
        import_definitions(conn, read_csv(legacy_dir / "definitions.csv"), stats)
    return stats


def write_report(stats: ImportStats, path: Path) -> None:
    terms = ", ".join(f"{lang} {n}" for lang, n in stats.terms.items())
    lines = [
        "# Import report: Google Sheet snapshot -> database",
        "",
        "Written by `termquake import-sheet`. The data was imported exactly as typed in",
        "the sheet; nothing was split, corrected or trimmed. This report lists what was",
        "left out and what the team may want to look at.",
        "",
        f"- Entries: {stats.entries}",
        f"- Terms (one per filled cell): {sum(stats.terms.values())} ({terms})",
        f"- Definitions: {stats.definitions}",
        "",
        "## Left out",
        "",
    ]
    if stats.skipped:
        lines += ["| Where | Language | Why |", "|---|---|---|"]
        lines += [f"| {w} | {lang} | {why} |" for w, lang, why in stats.skipped]
    else:
        lines.append("Nothing.")
    lines += ["", "## Kept as typed, worth a look", ""]
    for kind, where in stats.notes.items():
        listed = ", ".join(where) if len(where) <= 40 else "see queries/ to list them"
        lines.append(f"- **{kind}** ({len(where)}): {listed}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
