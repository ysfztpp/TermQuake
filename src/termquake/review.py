"""Review lists for standardising one language (layer 2 of the data plan).

Rules written as code turn each cell into the terms it should become, so the
same data always gives the same proposal. A rule that cannot be sure marks
the cell "review". Suggestions for those cells are kept in
data/review/<lang>.suggestions.csv, each with its reason; they are only
suggestions until a person decides.

Proposal format, one term per line:
    debris
    rubble
    CPR [abbreviation]
    to crawl — note: on hands and knees like a baby
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

AUTO = "auto"  # the rule is sure; a reviewer only confirms
REVIEW = "review"  # a person has to decide

# Rule codes and the Turkish labels the review sheet shows.
RULES = {
    "synonyms": "Eş anlamlılar ayrı terim olur (' / ')",
    "slash_tight": "Bitişik '/' (eş anlamlı mı, kelime içi seçenek mi?)",
    "abbreviation": "Kısaltma ayrı terim olur",
    "note": "Parantez içi açıklama nota taşınır",
    "optional_part": "Parantez terimin isteğe bağlı parçası",
    "capital": "Büyük harfle başlıyor (özel ad mı?)",
    "missing": "Bu dilde terim yok",
    "duplicate": "Aynı terim başka bir kavramda da var",
    "content": "İçerik kontrolü (AI işaretledi)",
}

_ABBR = r"[A-Z][A-Z0-9]{1,9}(?:[ -][A-Za-z]+)?"
_ABBR_END = re.compile(rf"^(?P<full>.+?)\s*\((?P<abbr>{_ABBR})\)$")  # x (ABC)
_ABBR_START = re.compile(r"^(?P<abbr>[A-Z][A-Z0-9]{1,9})\s*\((?P<full>[^()]+)\)$")  # ABC (x)
_ABBR_DASH = re.compile(rf"^(?P<full>.+?)\s+-\s+(?P<abbr>{_ABBR})$")  # x - ABC
_NOTE_END = re.compile(
    r"^(?P<term>[^()\[\]]+?)\s*[(\[](?P<note>[^()\[\]]+)[)\]]$"
)  # x (note), x [note]
_PAREN = re.compile(r"\(")


@dataclass
class Row:
    entry_id: int
    domain: str
    text: str  # the cell as stored now
    terms: list[str] = field(default_factory=list)  # proposal, one term per line
    rules: list[str] = field(default_factory=list)
    status: str = AUTO
    reason: str = ""  # why (for suggestions)
    origin: str = "rule"  # "rule" or "ai" (who made the proposal)
    context: str = ""  # the Turkish term, shown next to the cell for reviewers


def _part(text: str, status: list[str], rules: list[str]) -> list[str]:
    """Proposal for one synonym (no ' / ' inside)."""
    if m := _ABBR_END.match(text) or _ABBR_DASH.match(text):
        rules.append("abbreviation")
        return [m["full"], f"{m['abbr']} [abbreviation]"]
    if m := _ABBR_START.match(text):
        rules.append("abbreviation")
        return [f"{m['abbr']} [abbreviation]", m["full"]]
    if m := _NOTE_END.match(text):
        rules.append("note")
        return [f"{m['term']} — note: {m['note']}"]
    if _PAREN.search(text):
        rules.append("optional_part")
        status.append(REVIEW)
        return [text]
    if re.search(r"\S/\S", text):
        rules.append("slash_tight")
        status.append(REVIEW)
        return [text]
    return [text]


def classify(entry_id: int, domain: str, text: str) -> Row:
    """What the rules propose for one term cell (expressions are not split)."""
    row = Row(entry_id, domain, text)
    status: list[str] = []
    parts = [p.strip() for p in text.split(" / ")] if " / " in text else [text]
    if len(parts) > 1:
        row.rules.append("synonyms")
    for part in parts:
        row.terms += _part(part, status, row.rules)
    first = text[:1]
    first_word = text.split()[0] if text.split() else ""
    if first.isupper() and not first_word.isupper() and not re.match(r"^[A-Z]-", first_word):
        row.rules.append("capital")
        status.append(REVIEW)
    row.status = REVIEW if status else AUTO
    return row


def read_suggestions(path: Path) -> dict[int, dict[str, str]]:
    """data/review/<lang>.suggestions.csv: entry_id, proposal (terms joined by ' | '), reason."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {int(r["entry_id"]): r for r in csv.DictReader(fh)}


def build_review(
    conn: sqlite3.Connection, lang: str, suggestions: dict[int, dict[str, str]] | None = None
) -> list[Row]:
    """Rows that the rules would change or that need a decision, ordered by entry."""
    suggestions = suggestions or {}
    entries = conn.execute(
        "SELECT e.id, coalesce(d.code, ''), t.text FROM entry e "
        "LEFT JOIN domain d ON d.id = e.domain_id "
        "LEFT JOIN term t ON t.entry_id = e.id AND t.lang = ? ORDER BY e.id",
        (lang,),
    ).fetchall()
    context = dict(conn.execute("SELECT entry_id, text FROM term WHERE lang = 'tr'"))
    counts: dict[str, list[int]] = {}
    for eid, _, text in entries:
        if text:
            counts.setdefault(text.casefold(), []).append(eid)
    out: list[Row] = []
    for eid, domain, text in entries:
        if text is None:
            out.append(Row(eid, domain, "", [], ["missing"], REVIEW))
            continue
        row = (
            Row(eid, domain, text, [text])
            if domain == "expressions"
            else classify(eid, domain, text)
        )
        others = [str(x) for x in counts[text.casefold()] if x != eid]
        if others:
            row.rules.append("duplicate")
            row.status = REVIEW
            row.reason = f"Same text as entry {', '.join(others)}."
        if s := suggestions.get(eid):
            if s["proposal"]:
                row.terms = [t.strip() for t in s["proposal"].split(" | ")]
            if not row.rules:
                row.rules.append("content")
            row.reason = (row.reason + " " + s["reason"]).strip()
            row.origin = "ai"
            row.status = REVIEW
        row.context = context.get(eid, "")
        if row.rules:
            out.append(row)
    return out


# --------------------------------------------------------------------------- review sheet

DECISIONS = ["Onay", "Ret", "Düzelt"]
HEADERS = [
    ("Kavram no", 10),
    ("Alan", 13),
    ("Türkçe (bağlam)", 28),
    ("Şu anki metin", 34),
    ("Önerilen terimler (her satır bir terim)", 40),
    ("Kural", 30),
    ("Durum", 16),
    ("Öneren", 9),
    ("Gerekçe", 50),
    ("Karar", 11),
    ("Düzeltilmiş terimler", 34),
    ("Yorum", 30),
    ("İnceleyen", 14),
]
GUIDE = [
    "TermQuake: terim standardizasyonu, inceleme formu",
    "",
    "Bu dosya bir inceleme formudur, veritabanı değildir. Kararlar buradan okunur, "
    "veritabanına kodla uygulanır ve GitHub'da gözden geçirilir.",
    "",
    "Nasıl doldurulur:",
    "1. Dil sekmesini açın (ör. English). Sarı satırlar karar bekliyor; beyaz satırları "
    "kurallar otomatik önerdi, sadece göz atıp onaylamanız yeterli.",
    "2. 'Karar' sütununda seçin: Onay (öneri doğru), Ret (hücre olduğu gibi kalsın) "
    "veya Düzelt (doğrusunu 'Düzeltilmiş terimler' sütununa yazın).",
    "3. Düzeltirken her terimi ayrı satıra yazın (hücrede Ctrl+Enter / Cmd+Enter). "
    "Kısaltmalar için sonuna [abbreviation], not için ' — note: ...' ekleyin.",
    "4. 'İnceleyen' sütununa adınızı yazın. Diğer sütunlara dokunmayın.",
    "",
    "'Öneren' sütunu: Kural = yazılı kuralın önerisi; AI = Claude'un önerisi (gerekçesi yanında). "
    "AI önerileri yalnızca öneridir; kararı siz verirsiniz.",
    "İfadeler (cümleler) bu turda değişmiyor; ayrı kurallarla ele alınacak.",
]
STYLE_QUESTIONS = [
    (
        "Yazım: İngiliz mi Amerikan mı?",
        "Veride ikisi karışık: 'anaemia', 'anaesthetist' (UK) ile "
        "'hemorrhage', 'hematoma' (US). Öneri: ikisi de kalsın, ileride her terime bölge notu eklenir.",
    ),
    (
        "Büyük harf",
        "Terimler küçük harfle başlar; özel adlar (AFAD, Heimlich) ve kısaltmalar hariç.",
    ),
    (
        "Ana terim",
        "Bir hücrede birden fazla terim varsa, ilk yazılan ana terim olur (sitede önce o görünür).",
    ),
]


def write_review_xlsx(
    rows: list[Row], lang_name: str, path: Path, rule_counts: dict[str, int]
) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    guide = wb.active
    guide.title = "Nasıl kullanılır"
    for i, line in enumerate(GUIDE, start=1):
        guide.cell(i, 1, line).alignment = Alignment(wrap_text=True, vertical="top")
    guide["A1"].font = Font(bold=True, size=14)
    guide.column_dimensions["A"].width = 110

    rules = wb.create_sheet("Kurallar")
    rules.append(["Kural", "Ne yapar", f"{lang_name}: satır"])
    for code, label in RULES.items():
        rules.append([code, label, rule_counts.get(code, 0)])
    rules.append([])
    rules.append(["Stil sorusu (ekip kararı)", "Durum ve öneri"])
    for q, a in STYLE_QUESTIONS:
        rules.append([q, a])
    for cell in rules[1]:
        cell.font = Font(bold=True)
    rules.cell(len(RULES) + 3, 1).font = Font(bold=True)
    rules.column_dimensions["A"].width = 30
    rules.column_dimensions["B"].width = 90
    rules.column_dimensions["C"].width = 14
    for row in rules.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    ws = wb.create_sheet(lang_name)
    ws.append([h for h, _ in HEADERS])
    for i, (_, width) in enumerate(HEADERS, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = width
        ws.cell(1, i).font = Font(bold=True, color="FFFFFF")
        ws.cell(1, i).fill = PatternFill("solid", fgColor="1F4E79")
    review_fill = PatternFill("solid", fgColor="FFF2CC")
    ordered = sorted(rows, key=lambda r: (r.status != REVIEW, r.entry_id))
    for r in ordered:
        ws.append(
            [
                r.entry_id,
                r.domain,
                r.context,
                r.text,
                "\n".join(r.terms),
                "\n".join(RULES[x] for x in r.rules),
                "İnceleme gerekli" if r.status == REVIEW else "Otomatik",
                "AI" if r.origin == "ai" else "Kural",
                r.reason,
                "",
                "",
                "",
                "",
            ]
        )
        if r.status == REVIEW:
            for cell in ws[ws.max_row]:
                cell.fill = review_fill
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"J2:J{max(ws.max_row, 2)}")
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = ws.dimensions
    wb.active = wb.index(ws)
    wb.save(path)
