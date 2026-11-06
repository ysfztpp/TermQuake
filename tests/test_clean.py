"""Mechanical clean-up: invisible fixes only, never a change to the words."""

import sqlite3

import pytest
from conftest import execute, query

from termquake.clean import clean_database, clean_text
from termquake.cli import main
from termquake.config import REPO_ROOT
from termquake.db import load


@pytest.mark.parametrize(
    ("lang", "before", "after", "rules"),
    [
        ("tr", "mahsur kalmış ", "mahsur kalmış", ["space"]),
        ("ru", "обломки\n", "обломки", ["space"]),
        ("ru", "группа по  вопросам", "группа по вопросам", ["space"]),
        ("en", "drop, cover\n(hold on)", "drop, cover (hold on)", ["space"]),
        ("tr", "i̇ç organlar", "iç organlar", ["turkish_dotted_i"]),
        ("ko", "두개내_x0002_ 출혈", "두개내 출혈", ["spreadsheet_code"]),
        ("sv", "stöd­konstruktion", "stödkonstruktion", ["invisible"]),
        (
            "hi",
            "\u0938\u095e\u093e\u0908",
            "\u0938\u092b\u093c\u093e\u0908",
            ["unicode_nfc"],
        ),  # सफ़ाई
    ],
)
def test_rules(lang, before, after, rules):
    assert clean_text(before, lang) == (after, rules)


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("fa", "کم‌خونی"),  # zero-width non-joiner is Persian spelling
        ("en", "debris / rubble"),  # separators are content decisions, not mechanical
        ("de", "Unterkunft - unterkommen"),
        ("en", "Please move away from the area."),
        ("lt", "i̇"),  # the Turkish rule is for Turkish only
    ],
)
def test_words_and_separators_are_never_changed(lang, text):
    assert clean_text(text, lang) == (text, [])


def test_clean_is_idempotent():
    once, _ = clean_text(" a ­ b\n", "en")
    assert clean_text(once, "en") == (once, [])


def test_clean_database_and_check(imported, capsys):
    root = ["--root", str(imported.root)]
    assert main([*root, "clean", "--check"]) == 1  # the fixture has a trailing space and i̇
    assert "texts need cleaning" in capsys.readouterr().err
    assert main([*root, "clean"]) == 0
    assert query(imported, "SELECT text FROM term WHERE entry_id = 17 AND lang = 'tr'") == [
        ("mahsur kalmış",)
    ]
    assert main([*root, "clean", "--check"]) == 0


def test_check_changes_nothing(imported):
    execute(imported, "UPDATE term SET text = ' x ' WHERE entry_id = 1 AND lang = 'en'")
    conn = sqlite3.connect(imported.database)
    try:
        stats = clean_database(conn, apply=False)
        assert stats.changed["term.text"] >= 1
    finally:
        conn.close()
    assert query(imported, "SELECT text FROM term WHERE entry_id = 1 AND lang = 'en'") == [(" x ",)]


def test_the_committed_data_is_clean():
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript((REPO_ROOT / "db" / "schema.sql").read_text("utf-8"))
        load(conn, REPO_ROOT / "data" / "db")
        stats = clean_database(conn, apply=False)
    finally:
        conn.close()
    assert sum(stats.changed.values()) == 0, stats.changed
