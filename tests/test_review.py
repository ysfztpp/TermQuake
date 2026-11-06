"""Review rules: the same cell always gives the same proposal."""

import pytest

from termquake.review import AUTO, REVIEW, classify


@pytest.mark.parametrize(
    ("text", "terms", "rules", "status"),
    [
        ("debris / rubble", ["debris", "rubble"], ["synonyms"], AUTO),
        (
            "cardiopulmonary resuscitation (CPR)",
            ["cardiopulmonary resuscitation", "CPR [abbreviation]"],
            ["abbreviation"],
            AUTO,
        ),
        (
            "LPG (liquefied petroleum gas)",
            ["LPG [abbreviation]", "liquefied petroleum gas"],
            ["abbreviation"],
            AUTO,
        ),
        (
            "shortness of breath - SOB",
            ["shortness of breath", "SOB [abbreviation]"],
            ["abbreviation"],
            AUTO,
        ),
        ("shovel (tool)", ["shovel — note: tool"], ["note"], AUTO),
        ("dry goods [food]", ["dry goods — note: food"], ["note"], AUTO),
        ("(lever) jack", ["(lever) jack"], ["optional_part"], REVIEW),
        ("internal/external bleeding", ["internal/external bleeding"], ["slash_tight"], REVIEW),
        ("Suction set", ["Suction set"], ["capital"], REVIEW),
        ("D-ring", ["D-ring"], [], AUTO),
        ("tent", ["tent"], [], AUTO),
    ],
)
def test_classify(text, terms, rules, status):
    row = classify(1, "general", text)
    assert (row.terms, row.rules, row.status) == (terms, rules, status)
