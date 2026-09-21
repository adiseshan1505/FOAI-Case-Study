"""Tests for Horn-clause inference."""
import numpy as np
import pytest

from infodemic.kb.facts import generate_world, sample_kb_facts
from infodemic.kb.inference import KnowledgeBase, Verdict
from infodemic.kb.rules import RULES

FACTS = [
    ("capital_of", "city_0", "country_0"),
    ("part_of", "country_0", "region_1"),
    ("member_of", "country_0", "bloc_1"),
    ("member_of", "country_2", "bloc_1"),
    ("member_of", "country_3", "bloc_2"),
]


@pytest.fixture
def kb():
    return KnowledgeBase(FACTS, RULES)


@pytest.mark.parametrize(
    "atom, expected",
    [
        (("capital_of", "city_0", "country_0"), Verdict.TRUE),
        (("located_in", "city_0", "region_1"), Verdict.TRUE),
        (("allied", "country_0", "country_2"), Verdict.TRUE),
        (("located_in", "city_0", "region_2"), Verdict.FALSE),
        (("capital_of", "city_0", "country_5"), Verdict.FALSE),
        (("capital_of", "city_9", "country_0"), Verdict.FALSE),
        (("allied", "country_0", "country_3"), Verdict.FALSE),
        (("capital_of", "city_7", "country_7"), Verdict.UNKNOWN),
        (("allied", "country_0", "country_9"), Verdict.UNKNOWN),
    ],
)
def test_verify(kb, atom, expected):
    assert kb.verify(atom) is expected


def test_neq_builtin_requires_bound_distinct_terms():
    kb = KnowledgeBase([], [(("differs", "X", "Y"), (("neq", "X", "Y"),))])
    assert kb.holds(("differs", "a", "b"))
    assert not kb.holds(("differs", "a", "a"))
    assert not kb.holds(("differs", "A", "b"))


def test_recursive_rules_terminate():
    loop = [(("p", "X"), (("p", "X"),))]
    assert not KnowledgeBase([], loop).holds(("p", "a"))


def test_kb_is_sound_against_the_world():
    rng = np.random.default_rng(3)
    world = generate_world(rng)
    kb = KnowledgeBase(sample_kb_facts(world, 0.6, rng), RULES)
    for _ in range(500):
        assert kb.verify(world.true_atom(rng)) is not Verdict.FALSE
        assert kb.verify(world.false_atom(rng)) is not Verdict.TRUE


def test_partial_coverage_leaves_claims_unresolved():
    rng = np.random.default_rng(4)
    world = generate_world(rng)
    kb = KnowledgeBase(sample_kb_facts(world, 0.5, rng), RULES)
    verdicts = {kb.verify(world.false_atom(rng)) for _ in range(300)}
    assert Verdict.UNKNOWN in verdicts and Verdict.FALSE in verdicts
