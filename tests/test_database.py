"""The database: schema rules, build, dump and their safety checks."""

import sqlite3

import pytest
from conftest import execute, query

from termquake import SCHEMA_VERSION
from termquake.db import DatabaseError, build_database, dump_database


def snapshot(paths):
    return {p.name: p.read_bytes() for p in paths.data_db.glob("*.sql")}


def tr_term(paths, entry_id):
    return query(paths, "SELECT text FROM term WHERE entry_id = ? AND lang = 'tr'", entry_id)


# --------------------------------------------------------------------------- schema


def test_four_tables_and_one_view(imported):
    objects = query(
        imported,
        "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type, name",
    )
    assert objects == [
        ("table", "definition"),
        ("table", "domain"),
        ("table", "entry"),
        ("table", "term"),
        ("view", "entry_overview"),
    ]
    assert query(imported, "PRAGMA user_version") == [(SCHEMA_VERSION,)]


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO term(entry_id, lang, text) VALUES (1, 'de', 'Trümmer')",  # not a project language
        "INSERT INTO term(entry_id, lang, text) VALUES (470, 'en', '   ')",  # blank
        "INSERT INTO term(entry_id, lang, text) VALUES (5, 'tr', 'enkaz')",  # second cell for 5/tr
        "INSERT INTO term(entry_id, lang, text) VALUES (9999, 'en', 'ghost')",  # no such entry
        "INSERT INTO definition(entry_id, lang, text) VALUES (1, 'tr', 'a second definition')",
        "DELETE FROM domain WHERE code = 'first_aid'",  # entries still use it
    ],
)
def test_constraints_reject_bad_data(imported, sql):
    with pytest.raises(sqlite3.IntegrityError):
        execute(imported, sql)


def test_deleting_an_entry_deletes_its_terms_and_definitions(imported):
    execute(imported, "DELETE FROM entry WHERE id = 1")
    assert query(imported, "SELECT COUNT(*) FROM term WHERE entry_id = 1") == [(0,)]
    assert query(imported, "SELECT COUNT(*) FROM definition WHERE entry_id = 1") == [(0,)]


def test_overview_reads_like_the_sheet(imported):
    assert query(imported, "SELECT * FROM entry_overview WHERE id = 5") == [
        (5, "General Terms", "debris / rubble", "enkaz / moloz", "escombros", "Buna gerek var mı?")
    ]


# --------------------------------------------------------------------------- build and dump


def test_dump_is_canonical_and_round_trips(imported):
    assert dump_database(imported, check=True) == []
    before = snapshot(imported)
    build_database(imported)
    dump_database(imported)
    assert snapshot(imported) == before


def test_one_row_per_line(imported):
    lines = (imported.data_db / "term.sql").read_text("utf-8").splitlines()
    assert lines[0].startswith("-- TermQuake data: table term")
    prefix = "INSERT INTO term (id, entry_id, lang, text) VALUES ("
    assert all(line.startswith(prefix) and line.endswith(");") for line in lines[1:])


def test_an_edit_is_one_changed_line(imported):
    before = (imported.data_db / "term.sql").read_text("utf-8").splitlines()
    execute(
        imported,
        "UPDATE term SET text = 'enkaz / moloz / yıkıntı' WHERE entry_id = 5 AND lang = 'tr'",
    )
    assert dump_database(imported, check=True) == ["term.sql"]  # CI would catch an unsaved edit
    dump_database(imported)
    after = (imported.data_db / "term.sql").read_text("utf-8").splitlines()
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(changed) == 1 and "'enkaz / moloz / yıkıntı'" in changed[0][1]


def test_line_breaks_and_quotes_round_trip_exactly(imported):
    text = "it's line one\r\nline two\rline three\nend"
    conn = sqlite3.connect(imported.database)
    conn.execute("UPDATE definition SET text = ? WHERE entry_id = 1", (text,))
    conn.commit()
    conn.close()
    dump_database(imported)
    raw = (imported.data_db / "definition.sql").read_bytes()
    assert b"\r" not in raw and raw.count(b"\n") == 3  # header + 2 rows, each on one line
    build_database(imported)
    assert query(imported, "SELECT text FROM definition WHERE entry_id = 1") == [(text,)]


def test_hand_edit_of_a_data_file_builds(imported):
    path = imported.data_db / "term.sql"
    path.write_text(path.read_text("utf-8").replace("'enkaz / moloz'", "'enkaz'"), "utf-8")
    build_database(imported)
    assert tr_term(imported, 5) == [("enkaz",)]


def test_badly_formatted_hand_edit_is_caught_by_check_not_mistaken_for_an_edit(imported):
    path = imported.data_db / "domain.sql"
    path.write_text(path.read_text("utf-8").replace("VALUES (1, ", "VALUES (1,  "), "utf-8")
    build_database(imported)
    assert dump_database(imported, check=True) == ["domain.sql"]
    build_database(imported)  # not refused: nothing was edited in the database


def test_build_refuses_to_discard_unsaved_edits(imported):
    execute(imported, "UPDATE term SET text = 'enkaz' WHERE entry_id = 5 AND lang = 'tr'")
    with pytest.raises(DatabaseError, match="not saved"):
        build_database(imported)
    assert tr_term(imported, 5) == [("enkaz",)]
    build_database(imported, force=True)
    assert tr_term(imported, 5) == [("enkaz / moloz",)]


def test_dump_refuses_to_undo_changes_pulled_after_the_build(imported):
    path = imported.data_db / "term.sql"
    pulled = path.read_text("utf-8").replace("'escombros'", "'escombros (pl.)'", 1)
    path.write_text(pulled, "utf-8")  # e.g. a git pull brought someone's edit
    execute(imported, "UPDATE entry SET domain_id = 1 WHERE id = 468")
    with pytest.raises(DatabaseError, match="changed after"):
        dump_database(imported)
    assert path.read_text("utf-8") == pulled


def test_broken_reference_cannot_be_saved(imported):
    # e.g. a database tool with foreign keys switched off deleted an entry that has terms
    conn = sqlite3.connect(imported.database)
    conn.execute("DELETE FROM entry WHERE id = 5")
    conn.commit()
    conn.close()
    with pytest.raises(DatabaseError, match="broken references"):
        dump_database(imported)


def test_build_without_data_explains_what_to_do(workspace):
    with pytest.raises(DatabaseError, match="import-sheet"):
        build_database(workspace)
