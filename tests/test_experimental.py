"""Standardising cells into term rows, and filling gaps with labelled AI suggestions."""

import sqlite3

from conftest import execute, query

from termquake.ai import import_ai
from termquake.config import REPO_ROOT
from termquake.db import load
from termquake.standardise import parse_proposal, split_generic, standardise


def test_split_generic():
    assert split_generic("enkaz / moloz") == [
        ("enkaz", "fullForm", None),
        ("moloz", "fullForm", None),
    ]
    assert split_generic("сердечно-лёгочная реанимация (СЛР)") == [
        ("сердечно-лёгочная реанимация", "fullForm", None),
        ("СЛР", "abbreviation", None),
    ]
    assert split_generic("心肺蘇生法（CPR）")[1] == ("CPR", "abbreviation", None)
    # Not decided by a rule: gender slash, in-word slash, notes, a slash inside brackets.
    for text in ["herido/a", "iç/dış kanama", "kürek (alet)", "fay (hat / çizgi)"]:
        assert split_generic(text) == [(text, "fullForm", None)]


def test_parse_proposal():
    assert parse_proposal(["CPR [abbreviation]", "shovel — note: tool"]) == [
        ("CPR", "abbreviation", None),
        ("shovel", "fullForm", "tool"),
    ]


def test_standardise_keeps_ids_and_is_idempotent(imported):
    before = query(imported, "SELECT id FROM term WHERE entry_id = 5 AND lang = 'tr'")
    conn = sqlite3.connect(imported.database)
    try:
        assert sum(standardise(conn, REPO_ROOT / "data" / "review").values()) > 0
        assert sum(standardise(conn, REPO_ROOT / "data" / "review").values()) == 0
    finally:
        conn.close()
    rows = query(
        imported,
        "SELECT id, text, sort_order FROM term WHERE entry_id = 5 AND lang = 'tr' ORDER BY sort_order",
    )
    assert [(r[1], r[2]) for r in rows] == [("enkaz", 1), ("moloz", 2)]
    assert rows[0][0] == before[0][0]  # the first term keeps the row id
    # Expressions are never split.
    assert query(imported, "SELECT COUNT(*) FROM term WHERE entry_id = 149 AND lang = 'en'") == [
        (1,)
    ]


def test_ai_fills_only_gaps_and_is_labelled(imported, tmp_path):
    (tmp_path / "terms").mkdir()
    (tmp_path / "definitions").mkdir()
    (tmp_path / "terms" / "ar.tsv").write_text("# note\n5\tأنقاض | ركام\n1\tلا يكتب\n", "utf-8")
    (tmp_path / "definitions" / "en.tsv").write_text(
        "5\tBroken remains of a collapsed building.\n", "utf-8"
    )
    execute(imported, "DELETE FROM term WHERE entry_id = 5 AND lang = 'ar'")
    conn = sqlite3.connect(imported.database)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        terms, defs = import_ai(conn, tmp_path)
        again, _ = import_ai(conn, tmp_path)
    finally:
        conn.close()
    assert (terms["ar"], defs["en"], sum(again.values())) == (1, 1, 0)
    assert query(
        imported,
        "SELECT text, sort_order, origin, review_status FROM term WHERE entry_id = 5 AND lang = 'ar' ORDER BY sort_order",
    ) == [
        ("أنقاض", 1, "ai", "unreviewed"),
        ("ركام", 2, "ai", "unreviewed"),
    ]
    # Entry 1 already had an Arabic term: human text is never replaced.
    assert query(imported, "SELECT origin FROM term WHERE entry_id = 1 AND lang = 'ar'") == [
        ("sheet",)
    ]
    assert query(imported, "SELECT origin FROM definition WHERE entry_id = 5 AND lang = 'en'") == [
        ("ai",)
    ]


def test_committed_ai_terms_are_all_labelled():
    """Every text from data/ai/ is in the database with origin 'ai'."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript((REPO_ROOT / "db" / "schema.sql").read_text("utf-8"))
        load(conn, REPO_ROOT / "data" / "db")
        ai = dict(
            conn.execute(
                "SELECT lang, COUNT(DISTINCT entry_id) FROM term WHERE origin = 'ai' GROUP BY lang"
            )
        )
        for path in (REPO_ROOT / "data" / "ai" / "terms").glob("*.tsv"):
            lines = [x for x in path.read_text("utf-8").splitlines() if x and not x.startswith("#")]
            assert ai.get(path.stem, 0) >= len(lines), path.name
    finally:
        conn.close()
