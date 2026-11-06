"""Mechanical clean-up: fix how a text is stored, never what it says.

Each rule changes characters that a reader cannot see or that a computer
compares wrongly. No word, letter, separator or punctuation mark is changed;
splitting synonyms and other content decisions are separate steps
(docs/adr/0012-mechanical-cleanup.md).

The rules, in the order they run:

1. spreadsheet_code   Remove codes such as "_x0002_" that the xlsx export wrote
                      for invisible control characters.
2. turkish_dotted_i   Turkish only: "i" + combining dot above (looks like "i̇")
                      becomes "i". It comes from lower-casing "İ" with a tool
                      that does not know Turkish.
3. invisible          Remove soft hyphens and zero-width spaces. Zero-width
                      (non-)joiners are kept: they are part of correct spelling
                      in Persian and other scripts.
4. space              No-break spaces, tabs and line breaks become ordinary
                      spaces; runs of spaces become one; spaces at the start
                      and end are removed.
5. unicode_nfc        Unicode normalisation form C (the W3C and web standard),
                      so that the same letter is always stored the same way
                      and search and sorting find it.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

RULES = ["spreadsheet_code", "turkish_dotted_i", "invisible", "space", "unicode_nfc"]

_SPREADSHEET_CODE = re.compile(r"_x(000[0-8BCEF]|001[0-9A-F])_", re.I)  # control characters only
_INVISIBLE = re.compile("[­​⁠﻿]")  # soft hyphen, zero-width spaces, BOM
_SPACES = re.compile(r"[\s ]+")  # any whitespace, including no-break space and line breaks


def clean_text(text: str, lang: str) -> tuple[str, list[str]]:
    """The cleaned text and the names of the rules that changed it."""
    applied: list[str] = []

    def step(rule: str, new: str) -> None:
        nonlocal text
        if new != text:
            applied.append(rule)
            text = new

    step("spreadsheet_code", _SPREADSHEET_CODE.sub("", text))
    if lang == "tr":
        step("turkish_dotted_i", text.replace("i̇", "i"))
    step("invisible", _INVISIBLE.sub("", text))
    step("space", _SPACES.sub(" ", text).strip())
    step("unicode_nfc", unicodedata.normalize("NFC", text))
    return text, applied


@dataclass
class CleanStats:
    changed: Counter = field(default_factory=Counter)  # "table.column" -> values changed
    rules: Counter = field(default_factory=Counter)  # rule -> values changed by it


def clean_database(conn: sqlite3.Connection, *, apply: bool = True) -> CleanStats:
    """Clean every term and definition text (and definition source).

    With apply=False nothing is written: the result says what would change.
    """
    stats = CleanStats()
    targets = [("term", "text"), ("definition", "text"), ("definition", "source")]
    for table, column in targets:
        rows = conn.execute(
            f"SELECT id, lang, {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY id"
        ).fetchall()
        for row_id, lang, value in rows:
            cleaned, applied = clean_text(value, lang)
            if not applied:
                continue
            stats.changed[f"{table}.{column}"] += 1
            stats.rules.update(applied)
            if apply:
                conn.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (cleaned, row_id))
    if apply:
        conn.commit()
    return stats
