"""Data-quality checks, recomputed from the current database on every build.

Because the checks are a pure function of the data, the QA report is always
up to date: fix a term and its issue disappears at the next build. Results go
to the qa_issue table (not stored in data/db) and to data/QA_REPORT.md.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .config import Config
from .parse import Issue, is_placeholder, term_issues

ISSUE_HELP = {
    "placeholder_value": "Term text is a spreadsheet placeholder or error (#empty, #REF!).",
    "missing_pivot_term": "Entry has no term in the pivot language, so it cannot be found from it.",
    "missing_domain": "Entry has no domain.",
    "duplicate_term": "Same term (ignoring case and accents) in more than one entry. In the pivot language this usually means a duplicated entry.",
    "ambiguous_slash": "'/' without spaces: synonym, gender ending (ferido/a) or two concepts in one term?",
    "dash_separator": "' - ' inside a term: usually an acronym or a derived form.",
    "acronym_in_parentheses": "Acronym in brackets, e.g. '(CPR)'. Candidate for a separate acronym term.",
    "parenthetical": "Text in brackets may be an explanation rather than part of the term.",
    "comma_in_term": "Comma outside brackets may separate synonyms.",
    "definition_needs_review": "Definition contains a question; looks like a discussion note. Hidden on the website.",
    "definition_too_short": "Definition is very short or incomplete. Hidden on the website.",
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def definition_issues(text: str) -> Iterable[Issue]:
    if "?" in text:
        yield Issue(
            "warning",
            "definition_needs_review",
            f"{text[:80]!r}: contains a question; looks like a discussion note",
        )
    if len(text) < 15:
        yield Issue("warning", "definition_too_short", f"{text!r}")


def run_checks(conn: sqlite3.Connection, config: Config) -> dict[str, int]:
    """Replace the contents of qa_issue with fresh findings. Returns counts per issue code."""
    conn.execute("DELETE FROM qa_issue")
    counts: dict[str, int] = defaultdict(int)

    def add(entity_type: str, entity_id: int, issue: Issue, lang: str | None = None) -> None:
        conn.execute(
            "INSERT INTO qa_issue(entity_type, entity_id, severity, issue_type, lang, detail) "
            "VALUES (?,?,?,?,?,?)",
            (entity_type, entity_id, issue.severity, issue.code, lang, issue.detail),
        )
        counts[issue.code] += 1

    # Term text
    for term_id, lang, text, entry_type in conn.execute(
        "SELECT t.id, t.lang, t.text, c.entry_type FROM term t JOIN concept c ON c.id = t.concept_id "
        "WHERE c.status = 'active' AND t.review_status <> 'rejected'"
    ).fetchall():
        if is_placeholder(text):
            add("term", term_id, Issue("error", "placeholder_value", f"{text!r}"), lang)
            continue
        for issue in term_issues(text, is_phrase=entry_type == "phrase"):
            add("term", term_id, issue, lang)

    # Entries
    for cid, domain_id, entry_type in conn.execute(
        "SELECT id, domain_id, entry_type FROM concept WHERE status = 'active'"
    ).fetchall():
        if domain_id is None and entry_type == "term":
            add("concept", cid, Issue("warning", "missing_domain", "entry has no domain"))
    for (cid,) in conn.execute(
        "SELECT c.id FROM concept c WHERE c.status = 'active' AND NOT EXISTS "
        "(SELECT 1 FROM term t WHERE t.concept_id = c.id AND t.lang = ? AND t.review_status <> 'rejected')",
        (config.pivot,),
    ).fetchall():
        add(
            "concept",
            cid,
            Issue(
                "warning",
                "missing_pivot_term",
                f"no {config.pivot} term; the entry cannot be looked up from {config.pivot}",
            ),
            config.pivot,
        )

    # Duplicates: in the pivot language a repeated term usually means a duplicated entry;
    # in other languages one word legitimately translates related concepts.
    for lang, norm, concept_list in conn.execute(
        "SELECT t.lang, t.text_norm, group_concat(DISTINCT t.concept_id) FROM term t "
        "JOIN concept c ON c.id = t.concept_id WHERE c.status = 'active' "
        "GROUP BY t.lang, t.text_norm HAVING COUNT(DISTINCT t.concept_id) > 1"
    ).fetchall():
        ids = sorted(int(x) for x in concept_list.split(","))
        for term_id, concept_id, text in conn.execute(
            "SELECT id, concept_id, text FROM term WHERE lang = ? AND text_norm = ?", (lang, norm)
        ).fetchall():
            others = ", ".join(str(i) for i in ids if i != concept_id)
            severity = "warning" if lang == config.pivot else "info"
            add(
                "term",
                term_id,
                Issue(
                    severity,
                    "duplicate_term",
                    f"{text!r} also appears in entry {others} (possible duplicate entry)",
                ),
                lang,
            )

    # Definitions
    for did, lang, text in conn.execute("SELECT id, lang, text FROM definition").fetchall():
        for issue in definition_issues(text):
            add("definition", did, issue, lang)
    return dict(counts)


def issue_rows(conn: sqlite3.Connection) -> list[tuple]:
    rows = conn.execute("""
        SELECT q.severity, q.issue_type,
               CASE q.entity_type
                    WHEN 'concept' THEN q.entity_id
                    WHEN 'term' THEN (SELECT concept_id FROM term WHERE id = q.entity_id)
                    WHEN 'definition' THEN (SELECT concept_id FROM definition WHERE id = q.entity_id)
                    ELSE q.entity_id END AS entry,
               q.lang, q.detail
        FROM qa_issue q""").fetchall()
    return sorted(rows, key=lambda r: (SEVERITY_ORDER[r[0]], r[1], r[2], r[3] or "", r[4] or ""))


def write_report(conn: sqlite3.Connection, config: Config, path: Path) -> None:
    """data/QA_REPORT.md: coverage of every language, issues and a worklist for published ones."""
    total = conn.execute("SELECT COUNT(*) FROM concept WHERE status = 'active'").fetchone()[0]
    published = config.languages
    lines = [
        "# TermQuake data quality report",
        "",
        "Regenerated by `termquake dump` from the database in `data/db/`. Entry numbers are",
        "permanent IDs (the legacy sheet's **Nr.**). Published languages are marked ✓.",
        "",
        "## Coverage",
        "",
        "| Language | Published | Entries with a term | Coverage | Terms (incl. synonyms) |",
        "|---|:---:|---:|---:|---:|",
    ]
    coverage = conn.execute("""
        SELECT l.code, l.name_en, COUNT(DISTINCT t.concept_id), COUNT(t.id)
        FROM language l
        LEFT JOIN term t ON t.lang = l.code AND t.review_status <> 'rejected'
        GROUP BY l.code ORDER BY l.sort_order""").fetchall()
    # Published languages first, in publish order; then the rest by sort order.
    coverage.sort(key=lambda r: published.index(r[0]) if r[0] in published else len(published))
    for code, name, covered, terms in coverage:
        pct = 100 * covered / total if total else 0
        mark = "✓" if code in published else ""
        lines.append(f"| {name} (`{code}`) | {mark} | {covered} / {total} | {pct:.1f}% | {terms} |")

    rows = [r for r in issue_rows(conn) if r[3] is None or r[3] in published]
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for sev, code, *_ in rows:
        counts[(sev, code)] += 1
    lines += [
        "",
        "## Issues in published languages",
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
        "Errors and warnings in published languages, entry by entry. Run "
        "`SELECT * FROM qa_issue` on a built database for everything, including info items.",
        "",
    ]
    current = None
    for sev, code, entry, lang, detail in rows:
        if sev == "info":
            continue
        if code != current:
            current = code
            lines += ["", f"### `{code}` ({sev})", ""]
        lang_part = f" [{lang}]" if lang else ""
        lines.append(f"- Entry {entry}{lang_part}: {(detail or '').replace('|', chr(92) + '|')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
