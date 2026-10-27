"""Publish the database in the formats people need (build artifacts, not committed).

site/public/downloads/
    termquake.db    the SQLite database itself
    termquake.tbx   TBX-Basic (TerminOrgs v4, ISO 30042): for CAT tools and termbanks
    termquake.csv   one row per entry, like the old sheet: for spreadsheets
site/public/data/termbase.json
    compact data for the offline web app

Only languages listed in [publish] in termquake.toml are exported. Never
published: rejected terms and definitions, machine-made (MT/LLM) content that
no reviewer has approved, and definitions the QA checks flag (unless approved).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .config import Config, Paths

TBX_NS = "urn:iso:std:iso:30042:ed-2"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


@dataclass
class Entry:
    id: int
    domain: str | None
    entry_type: str
    terms: dict[str, list[str]]
    definitions: dict[str, dict]


# What may be published (ADR 0008): never anything rejected, and machine-made
# content (MT or LLM) only once a person has approved it.
def publishable(t: str) -> str:
    """SQL condition for a publishable row of table alias t (term or definition)."""
    return (
        f"{t}.review_status <> 'rejected' "
        f"AND ({t}.origin NOT IN ('mt', 'llm') OR {t}.review_status = 'approved')"
    )


def load_entries(conn: sqlite3.Connection, languages: list[str]) -> list[Entry]:
    entries: dict[int, Entry] = {}
    for cid, domain, etype in conn.execute(
        "SELECT c.id, d.code, c.entry_type FROM concept c LEFT JOIN domain d ON d.id = c.domain_id "
        "WHERE c.status = 'active' ORDER BY c.id"
    ):
        entries[cid] = Entry(cid, domain, etype, {}, {})
    for cid, lang, text in conn.execute(
        f"SELECT t.concept_id, t.lang, t.text FROM term t WHERE {publishable('t')} "
        "ORDER BY t.concept_id, t.lang, t.sort_order"
    ):
        if cid in entries and lang in languages:
            entries[cid].terms.setdefault(lang, []).append(text)
    # Definitions the QA checks flag are held back until a reviewer approves them:
    # an approval is a person's decision and outranks an automatic check.
    flagged = {
        did
        for (did,) in conn.execute(
            "SELECT entity_id FROM qa_issue WHERE entity_type = 'definition' "
            "AND severity IN ('error', 'warning') AND status = 'open'"
        )
    }
    for did, cid, lang, text, source, review, ok in conn.execute(
        "SELECT df.id, df.concept_id, df.lang, df.text, s.short_name, df.review_status, "
        f"({publishable('df')}) "
        "FROM definition df LEFT JOIN source s ON s.id = df.source_id ORDER BY df.concept_id, df.lang"
    ):
        if cid in entries and lang in languages:
            entries[cid].definitions[lang] = {
                "text": text,
                "source": source,
                "hidden": not ok or (did in flagged and review != "approved"),
            }
    return list(entries.values())


# --------------------------------------------------------------------------- TBX


def write_tbx(entries: list[Entry], conn: sqlite3.Connection, config: Config, path: Path) -> None:
    labels = dict(
        conn.execute(
            "SELECT d.code, l.label FROM domain d JOIN domain_label l ON l.domain_id = d.id AND l.lang = 'en'"
        )
    )
    ET.register_namespace("", TBX_NS)

    def q(tag: str) -> str:
        return f"{{{TBX_NS}}}{tag}"

    root = ET.Element(q("tbx"), {"type": "TBX-Basic", "style": "dca", XML_LANG: config.pivot})
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
        if e.domain:
            ET.SubElement(ce, q("descrip"), {"type": "subjectField"}).text = labels.get(
                e.domain, e.domain
            )
        for lang in config.languages:
            terms = e.terms.get(lang)
            if not terms:
                continue
            ls = ET.SubElement(ce, q("langSec"), {XML_LANG: lang})
            d = e.definitions.get(lang)
            if d and not d["hidden"]:
                grp = ET.SubElement(ls, q("descripGrp"))
                ET.SubElement(grp, q("descrip"), {"type": "definition"}).text = d["text"]
                if d["source"]:
                    ET.SubElement(grp, q("admin"), {"type": "source"}).text = d["source"]
            for term in terms:
                ts = ET.SubElement(ls, q("termSec"))
                ET.SubElement(ts, q("term")).text = term
                if e.entry_type == "phrase":
                    ET.SubElement(ts, q("termNote"), {"type": "termType"}).text = "phrase"
    ET.indent(root, space="  ")
    path.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")
    )


# --------------------------------------------------------------------------- CSV


def _cell(text: str) -> str:
    """Spreadsheet-safe cell: text starting with = + - @ is shown as text, never run
    as a formula (OWASP CSV injection), so a term can't execute code in Excel."""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def write_csv(entries: list[Entry], config: Config, path: Path) -> None:
    """One row per entry. UTF-8 with BOM so Excel shows Turkish characters correctly."""
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "id",
                "domain",
                "entry_type",
                *config.languages,
                *[f"definition_{lang}" for lang in config.languages],
            ]
        )
        for e in entries:
            defs = [e.definitions.get(lang) for lang in config.languages]
            w.writerow(
                [
                    e.id,
                    e.domain or "",
                    e.entry_type,
                    *[_cell(" / ".join(e.terms.get(lang, []))) for lang in config.languages],
                    *["" if not d or d["hidden"] else _cell(d["text"]) for d in defs],
                ]
            )


# --------------------------------------------------------------------------- web app data


def data_version(data_db: Path) -> str:
    """Fingerprint of the canonical data: changes exactly when the terminology changes."""
    h = hashlib.sha256()
    for path in sorted(data_db.glob("*.sql")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


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
    langs = {
        code: (name, native, direction)
        for code, name, native, direction in conn.execute(
            "SELECT code, name_en, name_native, direction FROM language"
        )
    }
    domain_labels: dict[str, dict[str, str]] = defaultdict(dict)
    for code, lang, label in conn.execute(
        "SELECT d.code, l.lang, l.label FROM domain d JOIN domain_label l ON l.domain_id = d.id ORDER BY d.id"
    ):
        domain_labels[code][lang] = label
    payload = {
        "schema": SCHEMA_VERSION,
        "data": {
            "version": data_version(paths.data_db),
            "updated": _data_date(paths.root),
            "pipeline": __version__,
            "commit": os.environ.get("GITHUB_SHA", "")[:12],
        },
        "languages": [
            {"code": c, "name": langs[c][0], "native": langs[c][1], "dir": langs[c][2]}
            for c in config.languages
        ],
        "domains": [{"code": code, "label": labels} for code, labels in domain_labels.items()],
        "entries": [_entry_json(e) for e in entries if e.terms],
        "moved": _moved(conn),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def _moved(conn: sqlite3.Connection) -> dict[str, int]:
    """Merged entries -> the entry that replaced them (following chains), so old links work."""
    merged = dict(
        conn.execute("SELECT id, merged_into FROM concept WHERE status = 'merged'").fetchall()
    )
    moved = {}
    for old in merged:
        target, seen = merged[old], {old}
        while target in merged and target not in seen:
            seen.add(target)
            target = merged[target]
        moved[str(old)] = target
    return moved


def _entry_json(e: Entry) -> dict:
    item: dict = {"id": e.id, "t": e.terms}
    if e.domain:
        item["d"] = e.domain
    if e.entry_type == "phrase":
        item["p"] = 1
    defs = {
        lang: {"x": d["text"], **({"s": d["source"]} if d["source"] else {})}
        for lang, d in e.definitions.items()
        if not d["hidden"]
    }
    if defs:
        item["def"] = defs
    return item


# --------------------------------------------------------------------------- entry point


class ExportError(RuntimeError):
    """Nothing to export from."""


def export_all(config: Config, paths: Paths) -> None:
    if not paths.database.exists():  # sqlite3.connect would silently create an empty one
        raise ExportError("build/termquake.db not found. Run `termquake build` first.")
    conn = sqlite3.connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise ExportError("Database schema version mismatch; rebuild with `termquake build`.")
        entries = load_entries(conn, config.languages)
        downloads = paths.site_public / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        write_tbx(entries, conn, config, downloads / "termquake.tbx")
        write_csv(entries, config, downloads / "termquake.csv")
        write_site_json(entries, conn, config, paths, paths.site_public / "data" / "termbase.json")
    finally:
        conn.close()
    shutil.copyfile(paths.database, downloads / "termquake.db")
