"""Publish the database in the formats people use (build outputs, never committed).

site/public/downloads/
    termquake.db    the SQLite database itself
    termquake.tbx   TBX-Basic (ISO 30042): for translation tools and termbanks
    termquake.csv   one row per entry, like the sheet: for spreadsheets
site/public/data/termbase.json
    compact data for the offline web app
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .config import Config, Paths
from .db import data_digest

TBX_NS = "urn:iso:std:iso:30042:ed-2"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Display data for the languages in termquake.toml.
LANGUAGE_NAMES = {
    "en": ("English", "English", "ltr"),
    "tr": ("Turkish", "Türkçe", "ltr"),
    "es": ("Spanish", "Español", "ltr"),
}


class ExportError(RuntimeError):
    """Nothing to export from."""


@dataclass
class Entry:
    id: int
    domain: str | None  # domain code
    terms: dict[str, str]  # lang -> cell text, as typed
    definitions: dict[str, tuple[str, str | None]]  # lang -> (text, source)


def load_entries(conn: sqlite3.Connection) -> list[Entry]:
    entries = {
        eid: Entry(eid, code, {}, {})
        for eid, code in conn.execute(
            "SELECT e.id, d.code FROM entry e LEFT JOIN domain d ON d.id = e.domain_id ORDER BY e.id"
        )
    }
    for eid, lang, text in conn.execute("SELECT entry_id, lang, text FROM term ORDER BY id"):
        entries[eid].terms[lang] = text
    for eid, lang, text, source in conn.execute(
        "SELECT entry_id, lang, text, source FROM definition ORDER BY id"
    ):
        entries[eid].definitions[lang] = (text, source)
    return list(entries.values())


# --------------------------------------------------------------------------- TBX


def write_tbx(entries: list[Entry], conn: sqlite3.Connection, config: Config, path: Path) -> None:
    """TBX-Basic: conceptEntry > langSec > termSec. Expressions are marked with the
    termType "phrase" rather than a subject field."""
    names = dict(conn.execute("SELECT code, name_en FROM domain"))
    ET.register_namespace("", TBX_NS)

    def q(tag: str) -> str:
        return f"{{{TBX_NS}}}{tag}"

    root = ET.Element(
        q("tbx"), {"type": "TBX-Basic", "style": "dca", XML_LANG: config.languages[0]}
    )
    file_desc = ET.SubElement(ET.SubElement(root, q("tbxHeader")), q("fileDesc"))
    ET.SubElement(
        ET.SubElement(file_desc, q("titleStmt")), q("title")
    ).text = "TermQuake: disaster relief and search & rescue terminology"
    ET.SubElement(ET.SubElement(file_desc, q("sourceDesc")), q("p")).text = (
        "Department of Translation and Interpreting Studies, Boğaziçi University, and volunteers. "
        "Licensed CC BY-NC 4.0. https://github.com/ysfztpp/TermQuake"
    )
    body = ET.SubElement(ET.SubElement(root, q("text")), q("body"))
    for e in entries:
        if not e.terms:
            continue
        ce = ET.SubElement(body, q("conceptEntry"), {"id": f"tq{e.id}"})
        if e.domain and e.domain != "expressions":
            ET.SubElement(ce, q("descrip"), {"type": "subjectField"}).text = names[e.domain]
        for lang in config.languages:
            if lang not in e.terms:
                continue
            ls = ET.SubElement(ce, q("langSec"), {XML_LANG: lang})
            if lang in e.definitions:
                text, source = e.definitions[lang]
                grp = ET.SubElement(ls, q("descripGrp"))
                ET.SubElement(grp, q("descrip"), {"type": "definition"}).text = text
                if source:
                    ET.SubElement(grp, q("admin"), {"type": "source"}).text = source
            ts = ET.SubElement(ls, q("termSec"))
            ET.SubElement(ts, q("term")).text = e.terms[lang]
            if e.domain == "expressions":
                ET.SubElement(ts, q("termNote"), {"type": "termType"}).text = "phrase"
    ET.indent(root, space="  ")
    path.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")
    )


# --------------------------------------------------------------------------- CSV


def _cell(text: str) -> str:
    """Spreadsheet-safe: text starting with = + - @ is shown as text, never run as a
    formula (OWASP CSV injection)."""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def write_csv(entries: list[Entry], config: Config, path: Path) -> None:
    """One row per entry. UTF-8 with BOM so that Excel shows Turkish characters correctly."""
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["id", "domain", *config.languages, *[f"definition_{x}" for x in config.languages]]
        )
        for e in entries:
            w.writerow(
                [
                    e.id,
                    e.domain or "",
                    *[_cell(e.terms.get(lang, "")) for lang in config.languages],
                    *[_cell(e.definitions.get(lang, ("",))[0]) for lang in config.languages],
                ]
            )


# --------------------------------------------------------------------------- web app data


def _data_date(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", "data/db"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return dt.date.today().isoformat()


def write_site_json(
    entries: list[Entry], conn: sqlite3.Connection, config: Config, paths: Paths, path: Path
) -> None:
    """The web app shows text trimmed of surrounding spaces (display only: the
    database keeps every cell as typed)."""
    domains = [
        {"code": code, "label": {"en": en, "tr": tr, "es": es}}
        for code, en, tr, es in conn.execute(
            "SELECT code, name_en, name_tr, name_es FROM domain ORDER BY id"
        )
    ]
    payload = {
        "schema": SCHEMA_VERSION,
        "data": {
            "version": data_digest(paths.data_db),
            "updated": _data_date(paths.root),
            "pipeline": __version__,
            "commit": os.environ.get("GITHUB_SHA", "")[:12],
        },
        "languages": [
            {
                "code": c,
                "name": LANGUAGE_NAMES[c][0],
                "native": LANGUAGE_NAMES[c][1],
                "dir": LANGUAGE_NAMES[c][2],
            }
            for c in config.languages
        ],
        "domains": domains,
        "entries": [_entry_json(e) for e in entries if e.terms],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def _entry_json(e: Entry) -> dict:
    item: dict = {"id": e.id, "t": {lang: [text.strip()] for lang, text in e.terms.items()}}
    if e.domain:
        item["d"] = e.domain
    if e.definitions:
        item["def"] = {
            lang: {"x": text.strip(), **({"s": source.strip()} if source else {})}
            for lang, (text, source) in e.definitions.items()
        }
    return item


# --------------------------------------------------------------------------- entry point


def export_all(config: Config, paths: Paths) -> None:
    if not paths.database.exists():  # sqlite3.connect would silently create an empty file
        raise ExportError("build/termquake.db not found. Run `termquake build` first.")
    conn = sqlite3.connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise ExportError(
                "build/termquake.db has an older schema. Run `termquake build --force`."
            )
        entries = load_entries(conn)
        downloads = paths.site_public / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        write_tbx(entries, conn, config, downloads / "termquake.tbx")
        write_csv(entries, config, downloads / "termquake.csv")
        write_site_json(entries, conn, config, paths, paths.site_public / "data" / "termbase.json")
    finally:
        conn.close()
    shutil.copyfile(paths.database, downloads / "termquake.db")
