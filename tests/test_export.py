import csv
import json
import xml.etree.ElementTree as ET

from termquake.build import build_database
from termquake.export import export_all

TBX_NS = "{urn:iso:std:iso:30042:ed-2}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def run(config, paths):
    build_database(config, paths)
    export_all(config, paths)


def test_exports_are_deterministic(config, workspace):
    run(config, workspace)
    first = {p.name: p.read_bytes() for p in workspace.export.iterdir()}
    run(config, workspace)
    second = {p.name: p.read_bytes() for p in workspace.export.iterdir()}
    assert first == second
    assert set(first) == {
        "concepts.tsv",
        "terms.en.tsv",
        "terms.tr.tsv",
        "terms.es.tsv",
        "definitions.tsv",
        "qa_issues.tsv",
        "QA_REPORT.md",
    }


def test_terms_tsv(config, workspace):
    run(config, workspace)
    with (workspace.export / "terms.tr.tsv").open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    assert rows[0] == ["concept_id", "sort_order", "term"]
    assert ["5", "0", "enkaz"] in rows and ["5", "1", "moloz"] in rows


def test_tbx_is_wellformed_tbx_basic(config, workspace):
    run(config, workspace)
    root = ET.parse(workspace.site_public / "downloads" / "termquake.tbx").getroot()
    assert root.tag == f"{TBX_NS}tbx"
    assert root.get("type") == "TBX-Basic" and root.get("style") == "dca"
    entries = root.findall(f".//{TBX_NS}conceptEntry")
    assert len(entries) == 10
    first = next(e for e in entries if e.get("id") == "tq5")
    langs = [ls.get(XML_LANG) for ls in first.findall(f"{TBX_NS}langSec")]
    assert langs == ["en", "tr", "es"]
    tr_terms = [t.text for t in first.findall(f"{TBX_NS}langSec[@{XML_LANG}='tr']//{TBX_NS}term")]
    assert tr_terms == ["enkaz", "moloz"]
    phrase = next(e for e in entries if e.get("id") == "tq149")
    assert phrase.find(f".//{TBX_NS}termNote[@type='termType']").text == "phrase"


def test_site_json(config, workspace):
    run(config, workspace)
    data = json.loads((workspace.site_public / "data" / "termbase.json").read_text("utf-8"))
    assert [lang["code"] for lang in data["languages"]] == ["en", "tr", "es"]
    by_id = {e["id"]: e for e in data["entries"]}
    assert by_id[5]["t"]["tr"] == ["enkaz", "moloz"] and by_id[5]["d"] == "general"
    assert by_id[149]["p"] == 1 and "d" not in by_id[149]
    # Good definition is published; the flagged "Buna gerek var mı?" draft is not.
    assert by_id[1]["def"]["tr"]["s"] == "TDK"
    assert "def" not in by_id[5]
    # Placeholder English cell is not published as a term.
    assert "en" not in by_id[470]["t"]


def test_downloads(config, workspace):
    run(config, workspace)
    downloads = workspace.site_public / "downloads"
    assert {p.name for p in downloads.iterdir()} == {
        "termquake.db",
        "termquake.tbx",
        "termquake.csv",
    }
    raw = (downloads / "termquake.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM so Excel opens Turkish characters correctly
    with (downloads / "termquake.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    row5 = next(r for r in rows if r["id"] == "5")
    assert row5["tr"] == "enkaz / moloz"


def test_qa_report_mentions_worklist(config, workspace):
    run(config, workspace)
    report = (workspace.export / "QA_REPORT.md").read_text("utf-8")
    assert "| Turkish (`tr`) | 10 / 10 | 100.0% |" in report
    assert "Nr. 470 [en]: cell contains '#empty3'" in report
