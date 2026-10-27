"""The SQL database as source of truth: build, edit, dump, rebuild, QA."""

import sqlite3

import pytest

from termquake import SCHEMA_VERSION
from termquake.build import BuildError, build_database, dump_database
from termquake.export import export_all


def q(paths, sql, *args):
    conn = sqlite3.connect(paths.database)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def issues(paths, code):
    return q(
        paths,
        "SELECT entity_type, entity_id, severity, lang FROM qa_issue "
        "WHERE issue_type=? ORDER BY entity_id, lang",
        code,
    )


def snapshot(paths):
    files = {p.name: p.read_text("utf-8") for p in paths.data_db.glob("*.sql")}
    files["QA_REPORT.md"] = paths.qa_report.read_text("utf-8")
    return files


def write(conn_path, *statements):
    conn = sqlite3.connect(conn_path)
    for sql in statements:
        conn.execute(sql)
    conn.commit()
    conn.close()


def test_dump_is_canonical_and_round_trips(config, migrated):
    paths, _ = migrated
    check = dump_database(config, paths, check=True)
    assert check.stale_files == [] and not check.report_stale
    before = snapshot(paths)
    build_database(config, paths)
    dump_database(config, paths)
    assert snapshot(paths) == before


def test_dump_files_are_one_row_per_line(migrated):
    paths, _ = migrated
    lines = (paths.data_db / "term.sql").read_text("utf-8").splitlines()
    assert lines[0].startswith("-- TermQuake canonical data")
    assert all(line.startswith("INSERT INTO term (") and line.endswith(");") for line in lines[1:])


def test_edit_is_recorded_saved_and_rebuilt(config, migrated):
    paths, _ = migrated
    conn = sqlite3.connect(paths.database)
    conn.execute(
        "UPDATE term SET text='arama ve kurtarma', updated_by=1 WHERE concept_id=1 AND lang='tr'"
    )
    conn.commit()
    conn.close()

    assert dump_database(config, paths, check=True).stale_files  # CI would catch an unsaved edit
    dump_database(config, paths)
    term_sql = (paths.data_db / "term.sql").read_text("utf-8")
    assert "'arama ve kurtarma'" in term_sql and "'arama kurtarma'" not in term_sql
    # the revision log (JSON old/new values) is saved with the data
    assert '"arama ve kurtarma"' in (paths.data_db / "revision.sql").read_text("utf-8")

    build_database(config, paths)
    rev = q(paths, "SELECT action, old_values, new_values FROM revision")
    assert len(rev) == 1  # the rebuild did not log the load as edits
    assert '"arama kurtarma"' in rev[0][1] and '"arama ve kurtarma"' in rev[0][2]
    # the search key is derived: computed by the build, never stored in data/db
    assert q(paths, "SELECT text_norm FROM term WHERE concept_id=1 AND lang='tr'") == [
        ("arama ve kurtarma",)
    ]
    assert "text_norm" not in term_sql
    assert dump_database(config, paths, check=True).stale_files == []


def test_hand_edit_of_data_file_builds(config, migrated):
    """An edit made directly in data/db (on GitHub, in a pull request) is simply loaded."""
    paths, _ = migrated
    path = paths.data_db / "term.sql"
    path.write_text(path.read_text("utf-8").replace("'enkaz'", "'enkaz yığını'", 1), "utf-8")
    build_database(config, paths)
    assert ("enkaz yığını", "enkaz yigini") in q(paths, "SELECT text, text_norm FROM term")
    assert dump_database(config, paths, check=True).stale_files == []


def test_build_refuses_to_discard_unsaved_edits(config, migrated):
    paths, _ = migrated
    write(
        paths.database, "UPDATE term SET text='arama ve kurtarma' WHERE concept_id=1 AND lang='tr'"
    )
    with pytest.raises(BuildError, match="not saved"):
        build_database(config, paths)
    assert q(paths, "SELECT text FROM term WHERE concept_id=1 AND lang='tr'") == [
        ("arama ve kurtarma",)
    ]
    build_database(config, paths, force=True)  # discarding on purpose
    assert q(paths, "SELECT text FROM term WHERE concept_id=1 AND lang='tr'") == [
        ("arama kurtarma",)
    ]


def test_dump_refuses_to_undo_changes_pulled_after_build(config, migrated):
    """build, then `git pull` brings someone's edit, then dump: the pull must not be undone."""
    paths, _ = migrated
    path = paths.data_db / "term.sql"
    pulled = path.read_text("utf-8").replace("'enkaz'", "'enkaz yığını'", 1)
    path.write_text(pulled, "utf-8")
    write(paths.database, "UPDATE concept SET domain_id=1 WHERE id=468")
    with pytest.raises(BuildError, match="changed after"):
        dump_database(config, paths)
    assert path.read_text("utf-8") == pulled


def test_history_records_author_only_when_the_edit_names_one(config, migrated):
    paths, _ = migrated
    conn = sqlite3.connect(paths.database)
    conn.execute("INSERT INTO contributor(display_name, role) VALUES ('Ayşe', 'translator')")
    ayse = conn.execute("SELECT id FROM contributor WHERE display_name='Ayşe'").fetchone()[0]
    conn.execute(
        "UPDATE term SET text='moloz yığını' WHERE concept_id=5 AND lang='tr' AND text='moloz'"
    )
    conn.execute(
        f"UPDATE term SET text='arama ve kurtarma', updated_by={ayse} WHERE concept_id=1 AND lang='tr'"
    )
    conn.commit()
    rows = conn.execute("SELECT new_values, actor_id FROM revision ORDER BY id").fetchall()
    origins = conn.execute(
        "SELECT text, origin FROM term WHERE text IN ('moloz yığını', 'arama ve kurtarma')"
    ).fetchall()
    conn.close()
    assert [actor for _, actor in rows] == [None, ayse]  # never blamed on the import bot
    assert sorted(origins) == [("arama ve kurtarma", "human"), ("moloz yığını", "human")]


def test_line_breaks_round_trip_exactly(config, migrated):
    paths, _ = migrated
    text = "line one\r\nline two\rline three\nend"
    conn = sqlite3.connect(paths.database)
    conn.execute("UPDATE definition SET text = ? WHERE id = 1", (text,))
    conn.commit()
    conn.close()
    dump_database(config, paths)
    raw = (paths.data_db / "definition.sql").read_bytes()
    assert b"\r" not in raw  # one row per line: line breaks are written as char(13)/char(10)
    lines = raw.decode("utf-8").split("\n")
    assert all(line.startswith(("--", "INSERT")) or line == "" for line in lines)
    build_database(config, paths)
    assert q(paths, "SELECT text FROM definition WHERE id = 1") == [(text,)]
    assert dump_database(config, paths, check=True).stale_files == []


def test_merged_entry_may_point_forward_and_old_links_redirect(config, migrated):
    paths, _ = migrated
    write(paths.database, "UPDATE concept SET status='merged', merged_into=470 WHERE id=5")
    dump_database(config, paths)
    build_database(config, paths)  # concept 5 refers to a row loaded after it
    export_all(config, paths)
    data = (paths.site_public / "data" / "termbase.json").read_text("utf-8")
    assert '"moved":{"5":470}' in data


def test_broken_reference_cannot_be_saved(config, migrated):
    paths, _ = migrated
    # e.g. a concept deleted in a database GUI that has foreign keys switched off
    write(paths.database, "PRAGMA foreign_keys = OFF", "DELETE FROM concept WHERE id = 5")
    with pytest.raises(BuildError, match="broken references"):
        dump_database(config, paths)


def test_qa_checks_are_recomputed_from_data(config, migrated):
    paths, _ = migrated
    assert issues(paths, "missing_domain") == [("concept", 468, "warning", None)]
    assert issues(paths, "missing_pivot_term") == [("concept", 470, "warning", "en")]
    assert len(issues(paths, "ambiguous_slash")) == 3  # entry 65 in en, tr, es
    assert len(issues(paths, "acronym_in_parentheses")) == 3  # entry 88
    dupes = {(lang, sev) for _, _, sev, lang in issues(paths, "duplicate_term")}
    assert ("en", "warning") in dupes and ("tr", "info") in dupes and ("tr", "warning") not in dupes
    assert [r[2] for r in issues(paths, "definition_needs_review")] == ["warning"]

    # Fix the data and the finding disappears at the next build.
    conn = sqlite3.connect(paths.database)
    conn.execute("UPDATE concept SET domain_id=1 WHERE id=468")
    conn.commit()
    conn.close()
    dump_database(config, paths)
    build_database(config, paths)
    assert issues(paths, "missing_domain") == []


def test_schema_constraints(migrated):
    paths, _ = migrated
    conn = sqlite3.connect(paths.database)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE term SET usage_status='best' WHERE id=1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO term(concept_id, lang, text, text_norm) VALUES (1,'xx','a','a')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO review_vote(target_type, target_id, contributor_id, vote) "
            "VALUES ('term', 1, 1, 2)"
        )
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_vote_threshold_view(migrated):
    paths, _ = migrated
    conn = sqlite3.connect(paths.database)
    conn.executemany(
        "INSERT INTO contributor(display_name, role) VALUES (?, 'validator')",
        [("a",), ("b",), ("c",)],
    )
    ids = [r[0] for r in conn.execute("SELECT id FROM contributor WHERE role='validator'")]
    conn.executemany(
        "INSERT INTO review_vote(target_type, target_id, contributor_id, vote) VALUES ('term', 1, ?, ?)",
        [(ids[0], 1), (ids[1], 1), (ids[2], -1)],
    )
    assert conn.execute("SELECT score, passes_threshold FROM v_vote_tally").fetchall() == [(1, 0)]
    conn.close()


def test_build_without_data_explains_what_to_do(config, workspace):
    with pytest.raises(BuildError, match="migrate"):
        build_database(config, workspace)
