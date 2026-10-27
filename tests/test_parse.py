import pytest

from termquake.parse import is_placeholder, parse_cell


def codes(parsed):
    return sorted(
        {i.code for i in parsed.issues} | {i.code for t in parsed.terms for i in t.issues}
    )


@pytest.mark.parametrize(
    ("cell", "terms"),
    [
        ("enkaz / moloz", ["enkaz", "moloz"]),
        ("herido / herida / víctima", ["herido", "herida", "víctima"]),
        ("atrapado/ atrapada", ["atrapado", "atrapada"]),  # space on one side: synonyms
        ("lastimarse /estar herido", ["lastimarse", "estar herido"]),
        ("ferido/a", ["ferido/a"]),  # gender ending: not split
        ("internal/external bleeding", ["internal/external bleeding"]),
        ("tijera / tijeras / tijera", ["tijera", "tijeras"]),  # duplicate removed
        ("", []),
        ("   ", []),
    ],
)
def test_synonym_split(cell, terms):
    assert parse_cell(cell, is_phrase=False).texts == terms


def test_phrases_are_never_split():
    cell = "I need you to call the police / fire department."
    assert parse_cell(cell, is_phrase=True).texts == [cell]


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("internal/external bleeding", ["ambiguous_slash"]),
        ("shortness of breath - SOB", ["dash_separator"]),
        ("burkmak - burkulmak", ["dash_separator"]),
        ("automated external defibrillator (AED)", ["acronym_in_parentheses"]),
        ("shovel (tool)", ["parenthetical"]),
        ("dry goods [food]", ["parenthetical"]),
        ("toraks, göğüs kafesi", ["comma_in_term"]),
        ("ısırık (arı, akrep vs.)", ["parenthetical"]),  # comma inside brackets is fine
        ("i̇nme", ["fixed_dotted_i"]),
        ("enkaz / moloz", []),
    ],
)
def test_issue_detection(cell, expected):
    assert codes(parse_cell(cell, is_phrase=False)) == expected


@pytest.mark.parametrize("value", ["#empty1", "#empty", "#REF!", "#N/A", " #empty3 "])
def test_placeholders_are_dropped(value):
    assert is_placeholder(value)
    parsed = parse_cell(value, is_phrase=False)
    assert parsed.texts == []
    assert [i.severity for i in parsed.issues] == ["error"]


def test_hashtag_like_terms_are_not_placeholders():
    assert not is_placeholder("#112")
