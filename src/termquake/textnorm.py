"""Text cleaning and search-key folding.

Two different operations, deliberately kept apart:

* ``clean`` repairs encoding damage without changing what a term says
  (invisible characters, broken dotted-i, stray whitespace). Its output is
  what users see.
* ``fold`` builds a search key: case- and accent-insensitive, Turkish-aware,
  punctuation-free. It is never shown to users.

``fold`` must give exactly the same result as ``fold`` in site/src/fold.ts,
otherwise the web app and the database disagree on what matches. Both are
tested against tests/shared/fold_cases.json.
"""

from __future__ import annotations

import re
import unicodedata

# Invisible characters that sneak in from copy-paste and carry no meaning:
# zero-width space, word joiner, byte-order mark, soft hyphen.
# NOT zero-width (non-)joiners (U+200C/U+200D): they are part of correct
# spelling in Persian, Kurdish (Sorani), Indic scripts and emoji.
_INVISIBLE = re.compile("[​⁠﻿­]")
# "İ" lower-cased by a non-Turkish-aware tool becomes "i" + combining dot
# above (U+0307), which looks right but breaks search ("i̇ç" != "iç").
_BROKEN_DOTTED_I = re.compile("i̇")
_SPACES = re.compile(r"\s+")


def clean(text: str) -> tuple[str, list[str]]:
    """Return (cleaned_text, list_of_fix_codes)."""
    fixes: list[str] = []
    out = unicodedata.normalize("NFC", text)

    stripped = _INVISIBLE.sub("", out)
    if stripped != out:
        fixes.append("removed_invisible_chars")
        out = stripped

    repaired = _BROKEN_DOTTED_I.sub("i", out)
    if repaired != out:
        fixes.append("fixed_dotted_i")
        out = repaired

    out = out.replace(" ", " ")
    collapsed = _SPACES.sub(" ", out).strip()
    if collapsed != out.strip():
        fixes.append("collapsed_whitespace")
    return collapsed, fixes


def fold(text: str) -> str:
    """Search key: lowercase, no diacritics, Turkish i/ı unified, punctuation removed.

    "Sargı Bezi" -> "sargi bezi";  "İÇ ORGANLAR" -> "ic organlar";  "réplica" -> "replica"
    """
    s = unicodedata.normalize("NFKD", text)
    # Format characters (ZWNJ, ZWJ, ...) are dropped, not turned into spaces, so
    # Persian "مراقبت‌های" (with ZWNJ) and "مراقبتهای" (typed without it) match.
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    s = _strip_accents(s)
    s = s.replace("ı", "i").lower().replace("ß", "ss").replace("ς", "σ")
    # Letters, numbers and remaining marks form words; everything else separates words.
    s = "".join(ch if unicodedata.category(ch)[0] in "LNM" else " " for ch in s)
    return unicodedata.normalize("NFC", _SPACES.sub(" ", s).strip())


# Below U+0800: Latin, Greek, Cyrillic, Armenian, Hebrew, Arabic. In these scripts
# combining marks are accents/vowel points, so search ignores them. In Indic,
# Japanese etc. marks are part of the letter and must be kept.
_ACCENT_SCRIPTS_END = 0x0800


def _strip_accents(s: str) -> str:
    out: list[str] = []
    base = 0
    for ch in s:
        if unicodedata.category(ch) == "Mn":
            if base < _ACCENT_SCRIPTS_END:
                continue
        else:
            base = ord(ch)
        out.append(ch)
    return "".join(out)
