import json
from pathlib import Path

import pytest

from termquake.textnorm import clean, fold

CASES = json.loads((Path(__file__).parent / "shared" / "fold_cases.json").read_text("utf-8"))[
    "cases"
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_fold_shared_cases(text, expected):
    assert fold(text) == expected


def test_fold_turkish_keyboardless_query_matches():
    # Users without a Turkish keyboard type "sargi" for "sargı".
    assert fold("sargi bezi") == fold("Sargı Bezi")
    assert fold("iç") == fold("İÇ") == fold("ic")


@pytest.mark.parametrize(
    ("raw", "expected", "fixes"),
    [
        ("deprem ", "deprem", []),  # trailing space: trimmed silently
        ("​", "", ["removed_invisible_chars"]),
        ("i̇ç organlar", "iç organlar", ["fixed_dotted_i"]),
        ("a  b", "a b", ["collapsed_whitespace"]),
        ("enkaz / moloz", "enkaz / moloz", []),
    ],
)
def test_clean(raw, expected, fixes):
    assert clean(raw) == (expected, fixes)


def test_clean_keeps_persian_zero_width_non_joiner():
    # ZWNJ is part of correct Persian spelling; removing it would change the word.
    persian = "مراقبت‌های ویژه"
    assert clean(persian) == (persian, [])


def test_clean_keeps_meaning():
    # Cleaning must never change letters, punctuation or case.
    assert (
        clean("Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)")[0]
        == "Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"
    )
