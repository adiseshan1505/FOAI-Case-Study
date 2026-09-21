"""Hand-authored Horn-clause rules."""
from __future__ import annotations

from infodemic.kb.inference import Rule

RULES: list[Rule] = [
    (("located_in", "X", "R"), (("capital_of", "X", "C"), ("part_of", "C", "R"))),
    (("allied", "A", "B"), (("member_of", "A", "G"), ("member_of", "B", "G"), ("neq", "A", "B"))),
    (("not_capital_of", "X", "C"), (("capital_of", "X", "D"), ("neq", "C", "D"))),
    (("not_capital_of", "X", "C"), (("capital_of", "Y", "C"), ("neq", "X", "Y"))),
    (
        ("not_located_in", "X", "R"),
        (("capital_of", "X", "C"), ("part_of", "C", "S"), ("neq", "R", "S")),
    ),
    (
        ("not_allied", "A", "B"),
        (("member_of", "A", "G"), ("member_of", "B", "H"), ("neq", "G", "H")),
    ),
]
