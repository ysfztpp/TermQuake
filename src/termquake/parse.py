"""Turn one spreadsheet cell into term records plus data-quality issues.

The sheet's legend says "/" = synonym, "-" = derivation, "()" = explanation,
but the audit showed each symbol is used for several things:

  "/"   synonyms ("enkaz / moloz"), gender endings ("ferido/a"),
        two concepts in one cell ("internal/external bleeding")
  "-"   acronyms ("shortness of breath - SOB"), derived forms ("burkmak - burkulmak")
  "()"  acronyms ("(CPR)"), optional words ("(sudden) cardiac arrest"),
        disambiguators ("shovel (tool)"), explanations ("hırıltı (nefes)")

So the importer is deliberately conservative: it only splits the one case
that is unambiguous ("/" with a space on at least one side, outside
expressions) and keeps everything else verbatim, recording an issue so a
human (or a reviewed AI pass) can resolve it. Nothing is ever dropped: the
untouched cell is also kept in the legacy snapshot (data/legacy/).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .textnorm import clean

# A "/" with whitespace on at least one side separates synonyms.
_SYNONYM_SPLIT = re.compile(r"\s+/\s*|\s*/\s+")
_TIGHT_SLASH = re.compile(r"\S/\S")
_DASH_SEPARATOR = re.compile(r"\s[-–—]\s")
_ACRONYM_IN_PARENS = re.compile(r"\(\s*[A-ZÇĞİÖŞÜ0-9]{2,10}\s*\)")
_PLACEHOLDER = re.compile(r"^#(?:empty\d*|REF!|N/A|VALUE!|NAME\?|ERROR!|DIV/0!)$", re.I)


@dataclass(frozen=True)
class Issue:
    severity: str  # error | warning | info
    code: str
    detail: str = ""


@dataclass
class ParsedTerm:
    text: str
    issues: list[Issue] = field(default_factory=list)


@dataclass
class ParsedCell:
    terms: list[ParsedTerm] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)  # issues about the cell as a whole

    @property
    def texts(self) -> list[str]:
        return [t.text for t in self.terms]


def is_placeholder(text: str) -> bool:
    return bool(_PLACEHOLDER.match(text.strip()))


def parse_cell(raw: str, *, is_phrase: bool) -> ParsedCell:
    """Parse one language cell of one concept row."""
    result = ParsedCell()
    text, fixes = clean(raw)
    if not text:
        return result
    for fix in fixes:
        if fix != "collapsed_whitespace":  # too common to be worth a report line
            result.issues.append(Issue("info", fix, text))

    if is_placeholder(text):
        result.issues.append(
            Issue("error", "placeholder_value", f"cell contains {text!r}; ignored")
        )
        return result

    parts = [text] if is_phrase else [p.strip() for p in _SYNONYM_SPLIT.split(text)]
    parts = [p for p in parts if p]
    # Drop exact duplicates inside one cell ("ataque / ataque") but keep order.
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            result.issues.append(Issue("info", "duplicate_in_cell", part))
            continue
        seen.add(part)
        result.terms.append(ParsedTerm(part, term_issues(part, is_phrase=is_phrase)))
    return result


def term_issues(term: str, *, is_phrase: bool) -> list[Issue]:
    issues: list[Issue] = []
    if not is_phrase and _TIGHT_SLASH.search(term):
        issues.append(
            Issue(
                "warning",
                "ambiguous_slash",
                f"{term!r}: '/' without spaces may be a synonym, a gender ending "
                "or two concepts in one cell",
            )
        )
    if _DASH_SEPARATOR.search(term):
        issues.append(
            Issue(
                "warning",
                "dash_separator",
                f"{term!r}: ' - ' may separate an acronym or a derived form",
            )
        )
    if _ACRONYM_IN_PARENS.search(term):
        issues.append(
            Issue(
                "info", "acronym_in_parentheses", f"{term!r}: candidate for a separate acronym term"
            )
        )
    elif "(" in term or "[" in term:
        issues.append(
            Issue(
                "info",
                "parenthetical",
                f"{term!r}: bracketed text may be a note, not part of the term",
            )
        )
    if not is_phrase and "," in _outside_brackets(term):
        issues.append(Issue("info", "comma_in_term", f"{term!r}: comma may separate synonyms"))
    return issues


def _outside_brackets(text: str) -> str:
    depth = 0
    out = []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)
