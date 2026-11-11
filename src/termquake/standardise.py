"""Standardise the stored terms: one row per term (layer 2 of the data plan).

English uses the full review rules plus the suggestions in
data/review/en.suggestions.csv. Every other language gets only the two rules
that are safe without knowing the language:

- " / " (or " // ") separates synonyms;
- "full form (ABC)" ends with an abbreviation, when ABC is written in capitals.

Expressions (sentences) are never split. Nothing a rule cannot decide is
touched. Running it twice changes nothing.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path

from .review import build_review, read_suggestions

_SYNONYMS = re.compile(r"\s+//?\s+")
_ABBR_TAIL = re.compile(r"^(?P<full>.+?)\s*[(（](?P<abbr>[^()（）\s]{2,10})[)）]$")
_NOTE = re.compile(r"^(?P<text>.+?) — note: (?P<note>.+)$")

Term = tuple[str, str, str | None]  # text, term_type, note


def _balanced(text: str) -> bool:
    return text.count("(") == text.count(")") and text.count("（") == text.count("）")


def split_generic(text: str) -> list[Term]:
    """Language-independent split of one cell into terms."""
    parts = [p.strip() for p in _SYNONYMS.split(text)]
    if len(parts) > 1 and not all(p and _balanced(p) for p in parts):
        parts = [text]  # a slash inside brackets: leave the cell alone
    out: list[Term] = []
    for part in parts:
        m = _ABBR_TAIL.match(part)
        if m and m["abbr"].isupper() and sum(c.isalpha() for c in m["abbr"]) >= 2:
            out += [(m["full"], "fullForm", None), (m["abbr"], "abbreviation", None)]
        else:
            out.append((part, "fullForm", None))
    return out


def parse_proposal(lines: list[str]) -> list[Term]:
    """Review-sheet lines ('CPR [abbreviation]', 'x — note: y') as terms."""
    out: list[Term] = []
    for line in lines:
        ttype = "fullForm"
        if line.endswith(" [abbreviation]"):
            line, ttype = line.removesuffix(" [abbreviation]"), "abbreviation"
        m = _NOTE.match(line)
        out.append((m["text"], ttype, m["note"]) if m else (line, ttype, None))
    return out


def _dedupe(terms: list[Term]) -> list[Term]:
    seen: set[str] = set()
    return [t for t in terms if not (t[0].casefold() in seen or seen.add(t[0].casefold()))]


def _write(
    conn: sqlite3.Connection, entry_id: int, lang: str, old: str, terms: list[Term], phrase: bool
) -> None:
    """Replace the single row of (entry, lang) with `terms`; the first keeps the row id."""
    for i, (text, ttype, note) in enumerate(terms, start=1):
        # Text that was not in the sheet's cell is a suggestion, and is marked as one.
        origin = "sheet" if text.casefold() in old.casefold() else "ai"
        ttype = "phrase" if phrase else ttype
        if i == 1 and old:
            conn.execute(
                "UPDATE term SET text = ?, term_type = ?, note = ?, origin = ? "
                "WHERE entry_id = ? AND lang = ?",
                (text, ttype, note, origin, entry_id, lang),
            )
        else:
            conn.execute(
                "INSERT INTO term(entry_id, lang, text, sort_order, term_type, note, origin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry_id, lang, text, i, ttype, note, origin),
            )


def standardise(conn: sqlite3.Connection, review_dir: Path) -> Counter:
    """Split cells into term rows. Returns language -> cells changed."""
    changed: Counter = Counter()
    single = {
        (e, lang)
        for e, lang in conn.execute(
            "SELECT entry_id, lang FROM term GROUP BY entry_id, lang HAVING COUNT(*) = 1"
        )
    }
    expressions = {
        e
        for (e,) in conn.execute(
            "SELECT e.id FROM entry e JOIN domain d ON d.id = e.domain_id "
            "WHERE d.code = 'expressions'"
        )
    }

    # English: review rules + suggestions.
    suggestions = read_suggestions(review_dir / "en.suggestions.csv")
    for row in build_review(conn, "en", suggestions):
        if not row.terms or (row.text and (row.entry_id, "en") not in single):
            continue
        terms = _dedupe(parse_proposal(row.terms))
        if terms != [(row.text, "fullForm", None)]:
            _write(conn, row.entry_id, "en", row.text, terms, row.entry_id in expressions)
            changed["en"] += 1

    # Other languages: the two safe rules.
    rows = conn.execute(
        "SELECT entry_id, lang, text FROM term WHERE lang <> 'en' ORDER BY id"
    ).fetchall()
    for entry_id, lang, text in rows:
        if entry_id in expressions or (entry_id, lang) not in single:
            continue
        terms = _dedupe(split_generic(text))
        if len(terms) > 1:
            _write(conn, entry_id, lang, text, terms, False)
            changed[lang] += 1
    conn.commit()
    return changed
