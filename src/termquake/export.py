"""Export the SQLite termbase to every format people need.

Committed to git (data/export/) -- small, sorted, diff-friendly text:
    concepts.tsv, terms.<lang>.tsv, definitions.tsv, qa_issues.tsv, QA_REPORT.md
Published as downloads (site/public/downloads/) -- build artifacts, not committed:
    termquake.db (SQLite), termquake.tbx (TBX-Basic, ISO 30042), termquake.csv (spreadsheet)
Web app data (site/public/data/termbase.json) -- compact JSON the offline app loads.

Exports never contain timestamps or anything else that changes between two
builds of the same data, so a commit only appears when the terminology changed.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
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
from .fetch import snapshot_digest

ISSUE_HELP = {
    "placeholder_value": "Cell holds a spreadsheet placeholder or error (#empty, #REF!) instead of a term. Ignored.",
    "missing_nr": "Row has content but no number in the Nr. column, so it cannot be identified. Skipped.",
    "duplicate_nr": "Two rows share one Nr. The second row was skipped.",
    "missing_pivot_term": "Entry has no English term, so it cannot be found from English.",
    "missing_domain": "Domain cell is empty (often an invisible character). Entry has no domain.",
    "unknown_domain": "Domain label is not in termquake.toml.",
    "duplicate_term": "Same term (ignoring case and accents) appears in more than one entry. Often a duplicated row.",
    "ambiguous_slash": "'/' without spaces: synonym, gender ending (ferido/a) or two concepts in one cell? Not split.",
    "dash_separator": "' - ' inside a term: usually an acronym or a derived form. Not split.",
    "acronym_in_parentheses": "Acronym in brackets, e.g. '(CPR)'. Candidate for a separate acronym term.",
    "parenthetical": "Text in brackets may be an explanation rather than part of the term.",
    "comma_in_term": "Comma outside brackets may separate synonyms.",
    "definition_needs_review": "Definition contains a question; looks like a discussion note. Hidden on the website.",
    "definition_too_short": "Definition is very short or incomplete. Hidden on the website.",
    "definition_unknown_entry": "Definitions tab refers to an Nr. that does not exist.",
    "removed_invisible_chars": "Invisible characters (zero-width space etc.) were removed automatically.",
    "fixed_dotted_i": "Broken Turkish 'i̇' (i + combining dot) was repaired to 'i' automatically.",
    "duplicate_in_cell": "Same synonym listed twice in one cell. Kept once.",
    "unknown_column": "A sheet column is not mapped to a language in termquake.toml.",
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Entry:
    id: int
    domain: str | None
    entry_type: str
    terms: dict[str, list[str]]
    definitions: dict[str, dict]


# --------------------------------------------------------------------------- loading


def load_entries(conn: sqlite3.Connection, languages: list[str]) -> list[Entry]:
    entries: dict[int, Entry] = {}
    for cid, domain, etype in conn.execute(
        "SELECT c.id, d.code, c.entry_type FROM concept c LEFT JOIN domain d ON d.id = c.domain_id "
        "WHERE c.status = 'active' ORDER BY c.id"
    ):
        entries[cid] = Entry(cid, domain, etype, {}, {})
    for cid, lang, text in conn.execute(
        "SELECT concept_id, lang, text FROM term WHERE review_status <> 'rejected' "
        "ORDER BY concept_id, lang, sort_order"
    ):
        if cid in entries and lang in languages:
            entries[cid].terms.setdefault(lang, []).append(text)
    hidden = {
        did
        for (did,) in conn.execute(
            "SELECT entity_id FROM qa_issue WHERE entity_type='definition' "
            "AND severity IN ('error','warning') AND status='open'"
        )
    }
    for did, cid, lang, text, source in conn.execute(
        "SELECT df.id, df.concept_id, df.lang, df.text, s.short_name FROM definition df "
        "LEFT JOIN source s ON s.id = df.source_id ORDER BY df.concept_id, df.lang"
    ):
        if cid in entries and lang in languages:
            entries[cid].definitions[lang] = {
                "text": text,
                "source": source,
                "hidden": did in hidden,
            }
    return list(entries.values())


# --------------------------------------------------------------------------- TSV (committed)


def _tsv(path: Path, header: list[str], rows: list[list]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if v is None else str(v).replace("\t", " ") for v in row])
    path.write_text(buf.getvalue(), encoding="utf-8")


def write_tsv_exports(conn: sqlite3.Connection, config: Config, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("terms.*.tsv"):
        stale.unlink()
    _tsv(
        out / "concepts.tsv",
        ["id", "domain", "entry_type", "status"],
        conn.execute(
            "SELECT c.id, d.code, c.entry_type, c.status FROM concept c "
            "LEFT JOIN domain d ON d.id = c.domain_id ORDER BY c.id"
        ).fetchall(),
    )
    for lang in config.languages:
        _tsv(
            out / f"terms.{lang}.tsv",
            ["concept_id", "sort_order", "term"],
            conn.execute(
                "SELECT concept_id, sort_order, text FROM term WHERE lang=? "
                "ORDER BY concept_id, sort_order",
                (lang,),
            ).fetchall(),
        )
    _tsv(
        out / "definitions.tsv",
        ["concept_id", "lang", "definition", "source"],
        conn.execute(
            "SELECT df.concept_id, df.lang, df.text, s.short_name FROM definition df "
            "LEFT JOIN source s ON s.id = df.source_id ORDER BY df.concept_id, df.lang"
        ).fetchall(),
    )
    _tsv(out / "qa_issues.tsv", ["severity", "issue", "entry", "lang", "detail"], _issue_rows(conn))


def _issue_rows(conn: sqlite3.Connection) -> list[list]:
    rows = conn.execute("""
        SELECT q.severity, q.issue_type,
               CASE q.entity_type
                    WHEN 'concept' THEN q.entity_id
                    WHEN 'term' THEN (SELECT concept_id FROM term WHERE id = q.entity_id)
                    WHEN 'definition' THEN (SELECT concept_id FROM definition WHERE id = q.entity_id)
                    ELSE 'row ' || q.entity_id END AS entry,
               q.lang, q.detail
        FROM qa_issue q""").fetchall()
    return sorted(
        rows, key=lambda r: (SEVERITY_ORDER[r[0]], r[1], str(r[2]).zfill(8), r[3] or "", r[4] or "")
    )


# --------------------------------------------------------------------------- QA report


def write_qa_report(conn: sqlite3.Connection, config: Config, path: Path) -> None:
    total = conn.execute("SELECT COUNT(*) FROM concept WHERE status='active'").fetchone()[0]
    names = dict(conn.execute("SELECT code, name_en FROM language"))
    lines = [
        "# TermQuake data quality report",
        "",
        "Generated by `termquake export` from the latest sheet snapshot. Fix issues in the Google",
        "Sheet; the next sync regenerates this file. Entry numbers are the sheet's **Nr.** column.",
        "",
        "## Coverage",
        "",
        "| Language | Entries with a term | Coverage | Terms (incl. synonyms) |",
        "|---|---:|---:|---:|",
    ]
    for lang in config.languages:
        covered, terms = conn.execute(
            "SELECT COUNT(DISTINCT concept_id), COUNT(*) FROM term WHERE lang=?", (lang,)
        ).fetchone()
        pct = 100 * covered / total if total else 0
        lines.append(f"| {names[lang]} (`{lang}`) | {covered} / {total} | {pct:.1f}% | {terms} |")

    rows = _issue_rows(conn)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for sev, code, *_ in rows:
        counts[(sev, code)] += 1
    lines += [
        "",
        "## Issues by type",
        "",
        "| Severity | Issue | Count | Meaning |",
        "|---|---|---:|---|",
    ]
    for (sev, code), n in sorted(
        counts.items(), key=lambda kv: (SEVERITY_ORDER[kv[0][0]], kv[0][1])
    ):
        lines.append(f"| {sev} | `{code}` | {n} | {ISSUE_HELP.get(code, '')} |")

    lines += [
        "",
        "## Worklist",
        "",
        "Errors and warnings, entry by entry. Info-level items are in `qa_issues.tsv`.",
        "",
    ]
    current = None
    for sev, code, entry, lang, detail in rows:
        if sev == "info":
            continue
        if code != current:
            current = code
            lines += ["", f"### `{code}` ({sev})", ""]
        where = f"Nr. {entry}" if str(entry).isdigit() else str(entry)
        lang_part = f" [{lang}]" if lang else ""
        lines.append(f"- {where}{lang_part}: {_md(detail or '')}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- downloads


def write_tbx(entries: list[Entry], conn: sqlite3.Connection, config: Config, path: Path) -> None:
    """TBX-Basic (TerminOrgs v4) in TBX v3 DCA style, ISO 30042:2019."""
    labels = {
        code: label
        for code, label in conn.execute(
            "SELECT d.code, l.label FROM domain d JOIN domain_label l ON l.domain_id=d.id AND l.lang='en'"
        )
    }
    ns = "urn:iso:std:iso:30042:ed-2"
    ET.register_namespace("", ns)
    q = lambda tag: f"{{{ns}}}{tag}"  # noqa: E731
    root = ET.Element(
        q("tbx"),
        {
            "type": "TBX-Basic",
            "style": "dca",
            "{http://www.w3.org/XML/1998/namespace}lang": config.pivot,
        },
    )
    header = ET.SubElement(root, q("tbxHeader"))
    file_desc = ET.SubElement(header, q("fileDesc"))
    ET.SubElement(
        ET.SubElement(file_desc, q("titleStmt")), q("title")
    ).text = "TermQuake: disaster relief and search & rescue terminology"
    source_desc = ET.SubElement(file_desc, q("sourceDesc"))
    ET.SubElement(source_desc, q("p")).text = (
        "Department of Translation and Interpreting Studies, Boğaziçi University. "
        "Licensed CC BY-NC 4.0. https://github.com/ysfztpp/termquake"
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
            ls = ET.SubElement(
                ce, q("langSec"), {"{http://www.w3.org/XML/1998/namespace}lang": lang}
            )
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


def write_csv(entries: list[Entry], config: Config, path: Path) -> None:
    """One row per entry, like the original sheet. UTF-8 with BOM so Excel shows Turkish correctly."""
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
            defs = [e.definitions.get(lang, {}) for lang in config.languages]
            w.writerow(
                [
                    e.id,
                    e.domain or "",
                    e.entry_type,
                    *[" / ".join(e.terms.get(lang, [])) for lang in config.languages],
                    *["" if not d or d["hidden"] else d["text"] for d in defs],
                ]
            )


# --------------------------------------------------------------------------- web app data


def _data_date(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", "data/raw"],
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
    entries: list[Entry],
    conn: sqlite3.Connection,
    config: Config,
    paths: Paths,
    raw_dir: Path,
    path: Path,
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
            "version": snapshot_digest(raw_dir),
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
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


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


def export_all(config: Config, paths: Paths, raw_dir: Path | None = None) -> None:
    raw_dir = raw_dir or paths.raw
    conn = sqlite3.connect(paths.database)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise RuntimeError("Database schema version mismatch; rebuild with `termquake build`.")
        entries = load_entries(conn, config.languages)
        write_tsv_exports(conn, config, paths.export)
        write_qa_report(conn, config, paths.export / "QA_REPORT.md")

        downloads = paths.site_public / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        write_tbx(entries, conn, config, downloads / "termquake.tbx")
        write_csv(entries, config, downloads / "termquake.csv")
        write_site_json(
            entries, conn, config, paths, raw_dir, paths.site_public / "data" / "termbase.json"
        )
    finally:
        conn.close()
    shutil.copyfile(paths.database, downloads / "termquake.db")
