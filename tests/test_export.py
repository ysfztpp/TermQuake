import csv
import json
import xml.etree.ElementTree as ET

from termquake.export import export_all

TBX_NS = "{urn:iso:std:iso:30042:ed-2}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def test_tbx_is_wellformed_tbx_basic(config, migrated):
    paths, _ = migrated
    export_all(config, paths)
    root = ET.parse(paths.site_public / "downloads" / "termquake.tbx").getroot()
    assert root.tag == f"{TBX_NS}tbx"
    assert root.get("type") == "TBX-Basic" and root.get("style") == "dca"
    entries = root.findall(f".//{TBX_NS}conceptEntry")
    assert len(entries) == 10
    first = next(e for e in entries if e.get("id") == "tq5")
    # Only published languages, in publish order (German is in the database but not published).
    assert [ls.get(XML_LANG) for ls in first.findall(f"{TBX_NS}langSec")] == ["en", "tr", "es"]
    tr_terms = [t.text for t in first.findall(f"{TBX_NS}langSec[@{XML_LANG}='tr']//{TBX_NS}term")]
    assert tr_terms == ["enkaz", "moloz"]
    phrase = next(e for e in entries if e.get("id") == "tq149")
    assert phrase.find(f".//{TBX_NS}termNote[@type='termType']").text == "phrase"


def test_site_json(config, migrated):
    paths, _ = migrated
    export_all(config, paths)
    data = json.loads((paths.site_public / "data" / "termbase.json").read_text("utf-8"))
    assert [lang["code"] for lang in data["languages"]] == ["en", "tr", "es"]
    by_id = {e["id"]: e for e in data["entries"]}
    assert by_id[5]["t"]["tr"] == ["enkaz", "moloz"] and by_id[5]["d"] == "general"
    assert "de" not in by_id[1]["t"]
    assert by_id[149]["p"] == 1 and "d" not in by_id[149]
    assert by_id[1]["def"]["tr"]["s"] == "TDK"
    assert "def" not in by_id[5]  # flagged draft definition is not published
    assert "en" not in by_id[470]["t"]  # placeholder was never imported
    assert len(data["data"]["version"]) == 12


def test_downloads(config, migrated):
    paths, _ = migrated
    export_all(config, paths)
    downloads = paths.site_public / "downloads"
    assert {p.name for p in downloads.iterdir()} == {
        "termquake.db",
        "termquake.tbx",
        "termquake.csv",
    }
    assert (downloads / "termquake.csv").read_bytes().startswith(b"\xef\xbb\xbf")  # BOM for Excel
    with (downloads / "termquake.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert next(r for r in rows if r["id"] == "5")["tr"] == "enkaz / moloz"


def test_qa_report(config, migrated):
    paths, _ = migrated
    report = paths.qa_report.read_text("utf-8")
    assert "| Turkish (`tr`) | ✓ | 10 / 10 | 100.0% |" in report
    assert "| German (`de`) |  |" in report
    assert "Entry 470 [en]: no en term" in report
