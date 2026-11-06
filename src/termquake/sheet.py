"""Import the original Google Sheet (frozen snapshot in data/legacy/) into the database.

The import keeps the data exactly as typed in the sheet (docs/adr/0010, 0011):
every filled language cell becomes one `term` row with the cell's text unchanged, including synonyms written together ("enkaz / moloz"),
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

# Language rows: (id = display order, BCP 47 code, English name, own name,
# writing direction, the English name in the sheet's column header).
# The headers look like "Türkçe (Turkish)"; the name in brackets is matched.
LANGUAGES = [
    (1, "en", "English", "English", "ltr", "English"),
    (2, "tr", "Turkish", "Türkçe", "ltr", "Turkish"),
    (3, "es", "Spanish", "Español", "ltr", "Spanish"),
    (4, "de", "German", "Deutsch", "ltr", "German"),
    (5, "ru", "Russian", "Русский", "ltr", "Russian"),
    (6, "fr", "French", "Français", "ltr", "French"),
    (7, "kmr", "Kurdish (Kurmanji)", "Kurdî (Kurmancî)", "ltr", "Kurdish"),
    (8, "zza", "Zazaki", "Zazakî", "ltr", "Zazaki"),
    (9, "ar", "Arabic", "العربية", "rtl", "Arabic"),
    (10, "el", "Greek", "Ελληνικά", "ltr", "Greek"),
    (11, "ja", "Japanese", "日本語", "ltr", "Japanese"),
    (12, "he", "Hebrew", "עברית", "rtl", "Hebrew"),
    (13, "it", "Italian", "Italiano", "ltr", "Italian"),
    (14, "hy", "Armenian", "Հայերեն", "ltr", "Armenian"),
    (15, "nl", "Dutch", "Nederlands", "ltr", "Dutch"),
    (16, "zh-Hans", "Chinese (Simplified)", "简体中文", "ltr", "Chinese-S"),
    (17, "zh-Hant", "Chinese (Traditional)", "繁體中文", "ltr", "Chinese-T"),
    (18, "bg", "Bulgarian", "Български", "ltr", "Bulgarian"),
    (19, "ko", "Korean", "한국어", "ltr", "Korean"),
    (20, "fa", "Persian", "فارسی", "rtl", "Persian"),
    (21, "hi", "Hindi", "हिन्दी", "ltr", "Hindi"),
    (22, "pt", "Portuguese", "Português", "ltr", "Portuguese"),
    (23, "sv", "Swedish", "Svenska", "ltr", "Swedish"),
    (24, "ro", "Romanian", "Română", "ltr", "Romanian"),
    (25, "sr", "Serbian", "Српски", "ltr", "Serbian"),
    (26, "mk", "Macedonian", "Македонски", "ltr", "Macedonian"),
    (27, "hu", "Hungarian", "Magyar", "ltr", "Hungarian"),
    (28, "fi", "Finnish", "Suomi", "ltr", "Finnish"),
    (29, "sq", "Albanian", "Shqip", "ltr", "Albanian"),
    (30, "cs", "Czech", "Čeština", "ltr", "Czech"),
    (31, "pl", "Polish", "Polski", "ltr", "Polish"),
]
SHEET_COLUMNS = {header: code for _, code, *_, header in LANGUAGES}

PLACEHOLDER = re.compile(r"^#(empty\d*|N/A|REF!|VALUE!|NAME\?|DIV/0!|ERROR!?|NULL!)$", re.I)
_INVISIBLE = re.compile("[​‌‍⁠﻿­]")
_LANG_IN_HEADER = re.compile(r"\(([A-Za-z][A-Za-z\- ]*)\)")
# Spreadsheet placeholders in other scripts, e.g. Persian "#خالی3" ("#empty3").
_PLACEHOLDER_ANY_SCRIPT = re.compile(r"^#\w+\d*$")


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


def _columns(header: list[str], stats: ImportStats) -> tuple[int, int, dict[str, int]]:
    """Positions of the Nr. and Domain columns and of each language's column."""
    nr = domain = None
    langs: dict[str, int] = {}
    for i, raw in enumerate(header):
        name = _label(raw)
        if name == "Nr.":
            nr = i
        elif name == "Domain":
            domain = i
        elif name:
            key = name if name in SHEET_COLUMNS else None
            if key is None and (m := _LANG_IN_HEADER.search(name)):
                key = m.group(1).strip()
            if key in SHEET_COLUMNS:
                langs[SHEET_COLUMNS[key]] = i
            else:
                stats.skipped.append(
                    (f"column {i + 1}", "", f"unknown column {name!r}; not imported")
                )
    if nr is None or domain is None:
        raise SheetError("terms tab: the header row needs 'Nr.' and 'Domain' columns")
    if "en" not in langs:
        raise SheetError("terms tab: no English column")
    return nr, domain, langs


def _value(cell: str) -> str | None:
    """The cell's text exactly as typed, or None for an empty cell or a placeholder."""
    value = cell.strip()
    if not value or PLACEHOLDER.match(value) or _PLACEHOLDER_ANY_SCRIPT.match(value):
        return None
    return cell


# Zero-width non-joiner: part of correct spelling in Persian (e.g. "کم‌خونی").
_ZWNJ_LANGS = {"fa"}
# A control character written out by the xlsx export, e.g. "_x0002_".
_XLSX_ESCAPE = re.compile(r"_x[0-9A-Fa-f]{4}_")


def _observe(stats: ImportStats, text: str, where: str, lang: str = "") -> None:
    """Things worth a look, recorded in the report. Nothing is changed."""
    if text != text.strip():
        stats.note("Space at the start or end of the cell", where)
    if "̇" in text:
        stats.note("Letter i written as i + combining dot (looks like i̇)", where)
    checked = text.replace("\u200c", "") if lang in _ZWNJ_LANGS else text
    if _INVISIBLE.search(checked):
        stats.note("Invisible character in the cell", where)
    if _XLSX_ESCAPE.search(text):
        stats.note("Spreadsheet code for a control character (e.g. _x0002_)", where)
    if " / " in text:
        stats.note("Several terms in one cell, separated by ' / '", where)


def import_terms(
    conn: sqlite3.Connection, config: Config, rows: list[list[str]], stats: ImportStats
) -> None:
    """One `entry` per numbered row, one `term` per filled language cell."""
    head = next((i for i, r in enumerate(rows) if r and _label(r[0]) == "Nr."), None)
    if head is None:
        raise SheetError("terms tab: no header row (a row whose first cell is 'Nr.')")
    header = rows[head]
    nr_col, domain_col, lang_cols = _columns(header, stats)
    # Same order as the language table, so term ids follow the display order.
    order = [code for _, code, *_ in LANGUAGES if code in lang_cols]
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

        for lang in order:
            cell = row[lang_cols[lang]]
            text = _value(cell)
            if text is None:
                if cell.strip():
                    stats.skipped.append((f"entry {nr}", lang, f"placeholder {cell.strip()!r}"))
                continue
            _observe(stats, text, f"entry {nr} ({lang})", lang)
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
        "INSERT INTO language(id, code, name_en, name_native, direction) VALUES (?, ?, ?, ?, ?)",
        [row[:5] for row in LANGUAGES],
    )
    conn.executemany(
        "INSERT INTO domain(id, code, name_en, name_tr, name_es) VALUES (?, ?, ?, ?, ?)", DOMAINS
    )
    import_terms(conn, config, read_csv(terms_csv), stats)
    if (legacy_dir / "definitions.csv").exists():
        import_definitions(conn, read_csv(legacy_dir / "definitions.csv"), stats)
    return stats


def write_report(stats: ImportStats, path: Path) -> None:
    terms = ", ".join(f"{lang} {n}" for lang, n in stats.terms.items())
    languages = sum(1 for n in stats.terms.values() if n)
    lines = [
        "# Import report: Google Sheet snapshot -> database",
        "",
        "Written by `termquake import-sheet`. The data was imported exactly as typed in",
        "the sheet; nothing was split, corrected or trimmed. This report lists what was",
        "left out and what the team may want to look at.",
        "",
        f"- Entries: {stats.entries}",
        f"- Terms (one per filled cell): {sum(stats.terms.values())} in {languages} languages",
        f"  ({terms})",
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
