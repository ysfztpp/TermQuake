"""Downloads (TBX, CSV, SQLite) and the website data."""

import csv
import json
import xml.etree.ElementTree as ET

import pytest
from conftest import execute

from termquake.export import ExportError, export_all

TBX = "{urn:iso:std:iso:30042:ed-2}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


@pytest.fixture
def exported(config, imported):
    export_all(config, imported)
    return imported


def site(paths):
    return json.loads((paths.site_public / "data" / "termbase.json").read_text("utf-8"))


def csv_rows(paths):
    with (paths.site_public / "downloads" / "termquake.csv").open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_tbx_basic(exported):
    root = ET.parse(exported.site_public / "downloads" / "termquake.tbx").getroot()
    assert root.tag == f"{TBX}tbx" and root.get("type") == "TBX-Basic"
    entries = {e.get("id"): e for e in root.iter(f"{TBX}conceptEntry")}
    assert len(entries) == 10
    five = entries["tq5"]
    assert five.find(f"{TBX}descrip[@type='subjectField']").text == "General Terms"
    assert [ls.get(XML_LANG) for ls in five.findall(f"{TBX}langSec")] == ["en", "tr", "es"]
    assert five.find(f"{TBX}langSec[@{XML_LANG}='tr']//{TBX}term").text == "enkaz / moloz"
    one = entries["tq1"]
    assert one.find(f".//{TBX}descrip[@type='definition']").text.startswith("Enkaz altındaki")
    assert one.find(f".//{TBX}admin[@type='source']").text == "TDK"
    phrase = entries["tq149"]
    assert phrase.find(f"{TBX}descrip[@type='subjectField']") is None
    assert phrase.find(f".//{TBX}termNote[@type='termType']").text == "phrase"


def test_website_data(exported):
    data = site(exported)
    assert [lang["code"] for lang in data["languages"]] == ["en", "tr", "es"]
    assert [d["code"] for d in data["domains"]][-1] == "expressions"
    by_id = {e["id"]: e for e in data["entries"]}
    assert by_id[5]["t"]["tr"] == ["enkaz / moloz"] and by_id[5]["d"] == "general"
    assert by_id[17]["t"]["tr"] == ["mahsur kalmış"]  # shown without the trailing space
    assert by_id[1]["def"]["tr"] == {
        "x": "Enkaz altındaki kişileri bulma ve kurtarma çalışması.",
        "s": "TDK",
    }
    assert "en" not in by_id[470]["t"]
    assert "d" not in by_id[468]
    assert len(data["data"]["version"]) == 12


def test_downloads(exported):
    downloads = exported.site_public / "downloads"
    assert {p.name for p in downloads.iterdir()} == {
        "termquake.db",
        "termquake.tbx",
        "termquake.csv",
    }
    assert (downloads / "termquake.csv").read_bytes().startswith(b"\xef\xbb\xbf")  # BOM for Excel
    rows = csv_rows(exported)
    assert list(rows[0]) == [
        "id",
        "domain",
        "en",
        "tr",
        "es",
        "definition_en",
        "definition_tr",
        "definition_es",
    ]
    assert next(r for r in rows if r["id"] == "5")["tr"] == "enkaz / moloz"


def test_csv_cells_never_run_as_formulas(config, imported):
    execute(imported, "UPDATE term SET text = '=HYPERLINK(1)' WHERE entry_id = 1 AND lang = 'en'")
    export_all(config, imported)
    assert next(r for r in csv_rows(imported) if r["id"] == "1")["en"].startswith("'=")


def test_export_before_build_explains(config, workspace):
    with pytest.raises(ExportError, match="termquake build"):
        export_all(config, workspace)
    assert not workspace.database.exists()
