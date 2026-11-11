"""AI suggestions: terms and definitions for the gaps, always marked as AI.

Files (tab-separated, one line per entry: entry id, text):
    data/ai/terms/<lang>.tsv         several terms for one entry: " | " between them
    data/ai/definitions/<lang>.tsv

Rules:
- A suggestion only fills a gap. A language that already has a term for an
  entry (or a definition) is never touched.
- Every row is stored with origin = 'ai' and review_status = 'unreviewed',
  so the website, TBX and CSV can always tell it from human work.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path


def _read(path: Path) -> list[tuple[int, str]]:
    out = []
    for n, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        entry_id, _, text = line.partition("\t")
        if not entry_id.strip().isdigit() or not text.strip():
            raise ValueError(f"{path.name}:{n}: expected '<entry id><TAB><text>'")
        out.append((int(entry_id), text.strip()))
    return out


def import_ai(conn: sqlite3.Connection, ai_dir: Path) -> tuple[Counter, Counter]:
    """Load the suggestion files. Returns (terms added, definitions added) per language."""
    terms: Counter = Counter()
    definitions: Counter = Counter()
    languages = {code for (code,) in conn.execute("SELECT code FROM language")}
    entries = {e for (e,) in conn.execute("SELECT id FROM entry")}
    expressions = {
        e
        for (e,) in conn.execute(
            "SELECT e.id FROM entry e JOIN domain d ON d.id = e.domain_id "
            "WHERE d.code = 'expressions'"
        )
    }
    for path in sorted((ai_dir / "terms").glob("*.tsv")):
        lang = path.stem
        if lang not in languages:
            raise ValueError(f"{path.name}: no language {lang!r}")
        have = {e for (e,) in conn.execute("SELECT entry_id FROM term WHERE lang = ?", (lang,))}
        for entry_id, text in _read(path):
            if entry_id not in entries or entry_id in have:
                continue
            seen: set[str] = set()
            parts = [p.strip() for p in text.split(" | ") if p.strip()]
            parts = [p for p in parts if not (p.casefold() in seen or seen.add(p.casefold()))]
            for i, part in enumerate(parts, start=1):
                conn.execute(
                    "INSERT INTO term(entry_id, lang, text, sort_order, term_type, origin) "
                    "VALUES (?, ?, ?, ?, ?, 'ai')",
                    (entry_id, lang, part, i, "phrase" if entry_id in expressions else "fullForm"),
                )
            have.add(entry_id)
            terms[lang] += 1
    for path in sorted((ai_dir / "definitions").glob("*.tsv")):
        lang = path.stem
        if lang not in languages:
            raise ValueError(f"{path.name}: no language {lang!r}")
        have = {
            e for (e,) in conn.execute("SELECT entry_id FROM definition WHERE lang = ?", (lang,))
        }
        for entry_id, text in _read(path):
            if entry_id not in entries or entry_id in have:
                continue
            conn.execute(
                "INSERT INTO definition(entry_id, lang, text, origin) VALUES (?, ?, ?, 'ai')",
                (entry_id, lang, text),
            )
            have.add(entry_id)
            definitions[lang] += 1
    conn.commit()
    return terms, definitions
