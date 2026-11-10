"""Several terms per language (schema v4): order, type, note, origin."""

import csv
import json
import sqlite3
import xml.etree.ElementTree as ET

import pytest
from conftest import execute, query

from termquake.export import export_all

TBX = "{urn:iso:std:iso:30042:ed-2}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

SPLIT_ENTRY_5 = [
    "UPDATE term SET text = 'debris' WHERE entry_id = 5 AND lang = 'en'",
    "INSERT INTO term(entry_id, lang, text, sort_order) VALUES (5, 'en', 'rubble', 2)",
    "INSERT INTO term(entry_id, lang, text, sort_order, term_type, note, origin) "
    "VALUES (5, 'en', 'DBR', 3, 'abbreviation', 'invented for the test', 'ai')",
]


@pytest.fixture
def split(config, imported):
    for sql in SPLIT_ENTRY_5:
        execute(imported, sql)
    export_all(config, imported)
    return imported


def test_defaults_for_sheet_rows(imported):
    assert query(
        imported,
        "SELECT sort_order, term_type, note, origin, review_status FROM term "
        "WHERE entry_id = 5 AND lang = 'tr'",
    ) == [(1, "fullForm", None, "sheet", "unreviewed")]
    assert query(imported, "SELECT DISTINCT term_type FROM term WHERE entry_id = 149") == [
        ("phrase",)
    ]  # expressions are phrases


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO term(entry_id, lang, text, sort_order) VALUES (5, 'en', 'x', 1)",  # same place
        "INSERT INTO term(entry_id, lang, text, sort_order) VALUES (5, 'en', 'debris / rubble', 2)",
        "INSERT INTO term(entry_id, lang, text, sort_order, term_type) VALUES (5, 'en', 'x', 2, 'slang')",
        "INSERT INTO term(entry_id, lang, text, sort_order, origin) VALUES (5, 'en', 'x', 2, 'robot')",
        "INSERT INTO term(entry_id, lang, text, sort_order, note) VALUES (5, 'en', 'x', 2, ' ')",
        "INSERT INTO term(entry_id, lang, text, sort_order) VALUES (5, 'en', 'x', 0)",
    ],
)
def test_constraints(imported, sql):
    with pytest.raises(sqlite3.IntegrityError):
        execute(imported, sql)


def test_overview_joins_terms_in_order(split):
    assert query(split, "SELECT en FROM entry_overview WHERE id = 5") == [
        ("debris / rubble / DBR",)
    ]


def test_tbx_one_term_section_per_term(split):
    root = ET.parse(split.site_public / "downloads" / "termquake.tbx").getroot()
    five = next(e for e in root.iter(f"{TBX}conceptEntry") if e.get("id") == "tq5")
    en = five.find(f"{TBX}langSec[@{XML_LANG}='en']")
    sections = en.findall(f"{TBX}termSec")
    assert [s.find(f"{TBX}term").text for s in sections] == ["debris", "rubble", "DBR"]
    dbr = sections[2]
    assert dbr.find(f"{TBX}termNote[@type='termType']").text == "abbreviation"
    assert [n.text for n in dbr.findall(f"{TBX}note")] == [
        "invented for the test",
        "AI suggestion, not verified",
    ]


def test_csv_joins_terms(split):
    with (split.site_public / "downloads" / "termquake.csv").open(encoding="utf-8-sig") as fh:
        row = next(r for r in csv.DictReader(fh) if r["id"] == "5")
    assert row["en"] == "debris / rubble / DBR"


def test_site_data_details(split):
    data = json.loads((split.site_public / "data" / "termbase.json").read_text("utf-8"))
    five = next(e for e in data["entries"] if e["id"] == 5)
    assert five["t"]["en"] == ["debris", "rubble", "DBR"]
    assert five["m"] == {"en": [{}, {}, {"ab": 1, "n": "invented for the test", "ai": 1}]}
    one = next(e for e in data["entries"] if e["id"] == 1)
    assert "m" not in one  # no details, no extra bytes
