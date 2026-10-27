import sqlite3

import pytest

from termquake import SCHEMA_VERSION
from termquake.build import BuildError, build_database, map_columns


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


def test_entries_and_terms(built):
    paths, stats = built
    # 12 data rows: one without Nr. and one duplicate Nr. are skipped.
    assert stats.concepts == 10
    assert q(
        paths, "SELECT text FROM term WHERE concept_id=5 AND lang='tr' ORDER BY sort_order"
    ) == [("enkaz",), ("moloz",)]
    assert q(
        paths, "SELECT text FROM term WHERE concept_id=17 AND lang='es' ORDER BY sort_order"
    ) == [("atrapado",), ("atrapada",)]


def test_only_published_languages_are_imported(built):
    paths, _ = built
    assert {lang for (lang,) in q(paths, "SELECT DISTINCT lang FROM term")} == {"en", "tr", "es"}
    active = {c for (c,) in q(paths, "SELECT code FROM language WHERE is_active=1")}
    assert active == {"en", "tr", "es"}


def test_raw_cells_are_archived_losslessly(built):
    paths, _ = built
    # German and Arabic are not published, but their cells are kept in import_raw.
    assert q(
        paths,
        "SELECT raw_value FROM import_raw WHERE concept_id=1 AND column_name='Deutsch (German)'",
    ) == [("Suchen und Retten",)]
    assert q(
        paths,
        "SELECT raw_value FROM import_raw WHERE concept_id=17 AND column_name='Türkçe (Turkish)'",
    ) == [("mahsur kalmış ",)]


def test_expressions_become_phrases(built):
    paths, _ = built
    assert q(paths, "SELECT entry_type, domain_id FROM concept WHERE id=149") == [("phrase", None)]
    es = q(paths, "SELECT text, term_type FROM term WHERE concept_id=149 AND lang='es'")
    assert es == [("Por favor, aléjense / aléjense de aquí", "phrase")]


def test_quality_issues(built):
    paths, _ = built
    assert [r[0] for r in issues(paths, "missing_nr")] == ["row"]
    assert [r[0] for r in issues(paths, "duplicate_nr")] == ["row"]
    assert issues(paths, "placeholder_value") == [("concept", 470, "error", "en")]
    assert issues(paths, "missing_pivot_term") == [("concept", 470, "warning", "en")]
    assert issues(paths, "missing_domain") == [("concept", 468, "warning", None)]
    assert len(issues(paths, "ambiguous_slash")) == 3  # en, tr, es of entry 65
    assert len(issues(paths, "acronym_in_parentheses")) == 3  # entry 88
    assert len(issues(paths, "fixed_dotted_i")) == 1
    assert q(paths, "SELECT text, text_norm FROM term WHERE concept_id=403 AND lang='tr'") == [
        ("iç organlar", "ic organlar")
    ]


def test_duplicate_terms_are_warnings_only_in_pivot_language(built):
    paths, _ = built
    dupes = {(lang, sev) for _, _, sev, lang in issues(paths, "duplicate_term")}
    assert ("en", "warning") in dupes
    assert ("tr", "info") in dupes and ("es", "info") in dupes
    assert ("tr", "warning") not in dupes


def test_definitions(built):
    paths, stats = built
    assert stats.definitions == 2
    assert q(
        paths,
        "SELECT d.text, s.short_name FROM definition d JOIN source s ON s.id=d.source_id "
        "WHERE d.concept_id=1",
    ) == [("Enkaz altındaki kişileri bulma ve kurtarma çalışması.", "TDK")]
    assert [r[2] for r in issues(paths, "definition_needs_review")] == ["warning"]
    assert [r[0] for r in issues(paths, "definition_unknown_entry")] == ["row"]


def test_history_starts_after_import(built):
    paths, _ = built
    conn = sqlite3.connect(paths.database)
    assert conn.execute("SELECT COUNT(*) FROM revision").fetchone()[0] == 0
    conn.execute(
        "UPDATE term SET text='arama ve kurtarma', updated_by=1 WHERE concept_id=1 AND lang='tr'"
    )
    rev = conn.execute("SELECT action, old_values, new_values FROM revision").fetchall()
    conn.close()
    assert len(rev) == 1 and rev[0][0] == "update"
    assert '"arama kurtarma"' in rev[0][1] and '"arama ve kurtarma"' in rev[0][2]


def test_schema_constraints(built):
    paths, _ = built
    conn = sqlite3.connect(paths.database)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE term SET usage_status='best' WHERE id=1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO term(concept_id, lang, text, text_norm) VALUES (1,'xx','a','a')")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_missing_language_column_fails_loudly(config):
    header = ["Nr.", "English", "Domain", "Türkçe (Turkish)"]  # no Spanish column
    with pytest.raises(BuildError, match="es"):
        map_columns(header, config)


def test_header_matched_on_english_name(config):
    header = ["Nr.", "English", "Domain", "Türkçe (Turkish)", "Españo (Spanish)", " (Arabic) عربي"]
    cols = map_columns(header, config)
    assert cols.languages == {"en": 1, "tr": 3, "es": 4, "ar": 5}


def test_missing_snapshot(config, workspace):
    (workspace.raw / "terms.csv").unlink()
    with pytest.raises(BuildError, match="sync"):
        build_database(config, workspace)
