"""One-time migration from the legacy sheet snapshot."""

import sqlite3

import pytest

from termquake.build import BuildError, migrate
from termquake.legacy import map_columns


def q(paths, sql, *args):
    conn = sqlite3.connect(paths.database)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def test_entries_and_terms(migrated):
    paths, stats = migrated
    # 12 numbered rows in the fixture: one without Nr. and one duplicate Nr. are not imported.
    assert stats.concepts == 10
    assert q(
        paths, "SELECT text FROM term WHERE concept_id=5 AND lang='tr' ORDER BY sort_order"
    ) == [
        ("enkaz",),
        ("moloz",),
    ]
    assert q(
        paths, "SELECT text FROM term WHERE concept_id=17 AND lang='es' ORDER BY sort_order"
    ) == [
        ("atrapado",),
        ("atrapada",),
    ]


def test_every_language_is_migrated_not_only_published_ones(migrated):
    paths, stats = migrated
    assert set(stats.terms) == {"en", "tr", "es", "de", "ar"}
    assert q(paths, "SELECT text FROM term WHERE concept_id=1 AND lang='de'") == [
        ("Suchen und Retten",)
    ]


def test_expressions_become_phrases(migrated):
    paths, _ = migrated
    assert q(paths, "SELECT entry_type, domain_id FROM concept WHERE id=149") == [("phrase", None)]
    assert q(paths, "SELECT text, term_type FROM term WHERE concept_id=149 AND lang='es'") == [
        ("Por favor, aléjense / aléjense de aquí", "phrase")
    ]


def test_encoding_damage_is_repaired(migrated):
    paths, _ = migrated
    assert q(paths, "SELECT text, text_norm FROM term WHERE concept_id=403 AND lang='tr'") == [
        ("iç organlar", "ic organlar")
    ]
    assert q(paths, "SELECT text FROM term WHERE concept_id=17 AND lang='tr'") == [
        ("mahsur kalmış",)
    ]


def test_migration_report_lists_sheet_only_problems(migrated):
    paths, _ = migrated
    report = (paths.legacy / "MIGRATION_REPORT.md").read_text("utf-8")
    for code in (
        "missing_nr",
        "duplicate_nr",
        "placeholder_value",
        "unknown_column",
        "fixed_dotted_i",
        "definition_unknown_entry",
    ):
        assert code in report
    assert "'#empty3'" in report


def test_definitions(migrated):
    paths, stats = migrated
    assert stats.definitions == 2
    assert q(
        paths,
        "SELECT d.text, s.short_name FROM definition d JOIN source s ON s.id=d.source_id "
        "WHERE d.concept_id=1",
    ) == [("Enkaz altındaki kişileri bulma ve kurtarma çalışması.", "TDK")]


def test_migration_refuses_to_overwrite_the_database(config, migrated):
    paths, _ = migrated
    with pytest.raises(BuildError, match="source of truth"):
        migrate(config, paths)
    migrate(config, paths, force=True)  # explicit start-over is possible


def test_missing_language_column_fails_loudly(config):
    from termquake.legacy import MigrationError

    with pytest.raises(MigrationError, match="es"):
        map_columns(["Nr.", "English", "Domain", "Türkçe (Turkish)"], config)


def test_header_matched_on_english_name(config):
    header = ["Nr.", "English", "Domain", "Türkçe (Turkish)", "Españo (Spanish)", " (Arabic) عربي"]
    assert map_columns(header, config).languages == {"en": 1, "tr": 3, "es": 4, "ar": 5}
