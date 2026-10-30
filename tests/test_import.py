"""Importing the sheet snapshot: every cell exactly as typed."""

import pytest
from conftest import query

from termquake.cli import run_import
from termquake.sheet import SheetError


def test_cells_are_kept_exactly_as_typed(imported):
    terms = dict(
        ((eid, lang), text)
        for eid, lang, text in query(imported, "SELECT entry_id, lang, text FROM term")
    )
    assert terms[(5, "tr")] == "enkaz / moloz"  # synonyms stay together
    assert terms[(17, "tr")] == "mahsur kalmış "  # trailing space kept
    assert terms[(17, "es")] == "atrapado/ atrapada"
    assert terms[(403, "tr")] == "i̇ç organlar"  # i + combining dot, as typed
    assert terms[(88, "en")] == "automated external defibrillator (AED)"


def test_only_english_turkish_and_spanish(imported):
    assert {lang for (lang,) in query(imported, "SELECT DISTINCT lang FROM term")} == {
        "en",
        "tr",
        "es",
    }


def test_placeholders_and_empty_cells_have_no_row(imported):
    assert query(imported, "SELECT lang FROM term WHERE entry_id = 470") == [
        ("tr",)
    ]  # en was '#empty3'
    report = (imported.legacy / "IMPORT_REPORT.md").read_text("utf-8")
    assert "| entry 470 | en | placeholder '#empty3' |" in report


def test_rows_without_a_usable_number_are_reported(imported):
    assert query(imported, "SELECT COUNT(*) FROM entry") == [(10,)]
    report = (imported.legacy / "IMPORT_REPORT.md").read_text("utf-8")
    assert "no number in the Nr. column" in report
    assert "Nr. 1 is used twice" in report


def test_domains(imported):
    assert query(imported, "SELECT code FROM domain ORDER BY id") == [
        ("general",),
        ("search_rescue",),
        ("first_aid",),
        ("medical",),
        ("misc",),
        ("expressions",),
    ]
    domain_of = dict(
        query(imported, "SELECT e.id, d.code FROM entry e LEFT JOIN domain d ON d.id = e.domain_id")
    )
    assert domain_of[149] == "expressions"
    assert domain_of[65] == "first_aid"  # the sheet's typo "Fırst Aid" is matched as is
    assert domain_of[468] is None  # the cell held only an invisible character


def test_definitions_as_typed(imported):
    assert query(
        imported, "SELECT entry_id, lang, text, source FROM definition ORDER BY entry_id"
    ) == [
        (1, "tr", "Enkaz altındaki kişileri bulma ve kurtarma çalışması.", "TDK"),
        (5, "tr", "Buna gerek var mı?", None),
    ]
    assert "Nr. 999 does not exist" in (imported.legacy / "IMPORT_REPORT.md").read_text("utf-8")


def test_report_lists_what_to_look_at(imported):
    report = (imported.legacy / "IMPORT_REPORT.md").read_text("utf-8")
    assert "**Space at the start or end of the cell** (1): entry 17 (tr)" in report
    assert "entry 403 (tr)" in report


def test_import_refuses_to_overwrite_the_database(config, imported):
    with pytest.raises(SheetError, match="source of truth"):
        run_import(config, imported, force=False)
