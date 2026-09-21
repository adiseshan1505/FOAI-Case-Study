"""Horn-clause inference engine using backward chaining."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import Enum
from itertools import count

Atom = tuple[str, ...]
Rule = tuple[Atom, tuple[Atom, ...]]
Subst = dict[str, str]

MAX_DEPTH = 8


class Verdict(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


def is_var(term: str) -> bool:
    return term[:1].isupper()


def walk(term: str, subst: Subst) -> str:
    while is_var(term) and term in subst:
        term = subst[term]
    return term


def unify(a: Atom, b: Atom, subst: Subst) -> Subst | None:
    if len(a) != len(b):
        return None
    for x, y in zip(a, b):
        x, y = walk(x, subst), walk(y, subst)
        if x == y:
            continue
        if is_var(x):
            subst = {**subst, x: y}
        elif is_var(y):
            subst = {**subst, y: x}
        else:
            return None
    return subst


class KnowledgeBase:
    """Ground facts plus Horn rules, queried by backward chaining (SLD resolution).

    Constants are lowercase, variables start with an uppercase letter. The
    built-in body literal ("neq", A, B) succeeds when both terms are bound and
    differ. Negative knowledge is expressed with rules whose head predicate is
    "not_<predicate>", so verify() stays within pure Horn clauses.
    """

    def __init__(self, facts: Iterable[Atom], rules: Iterable[Rule]):
        self._facts: dict[str, list[Atom]] = {}
        for fact in facts:
            self._facts.setdefault(fact[0], []).append(fact)
        self._rules: dict[str, list[Rule]] = {}
        for rule in rules:
            self._rules.setdefault(rule[0][0], []).append(rule)
        self._fresh = count()
        self._cache: dict[Atom, Verdict] = {}

    def holds(self, goal: Atom) -> bool:
        return next(self._solve([goal], {}, 0), None) is not None

    def verify(self, atom: Atom) -> Verdict:
        if atom not in self._cache:
            if self.holds(atom):
                verdict = Verdict.TRUE
            elif self.holds(("not_" + atom[0], *atom[1:])):
                verdict = Verdict.FALSE
            else:
                verdict = Verdict.UNKNOWN
            self._cache[atom] = verdict
        return self._cache[atom]

    def _rename(self, rule: Rule) -> Rule:
        suffix = next(self._fresh)

        def rename(atom: Atom) -> Atom:
            return tuple(f"{t}_{suffix}" if is_var(t) else t for t in atom)

        head, body = rule
        return rename(head), tuple(rename(b) for b in body)

    def _solve(self, goals: list[Atom], subst: Subst, depth: int) -> Iterator[Subst]:
        if not goals:
            yield subst
            return
        goal, rest = goals[0], goals[1:]
        if goal[0] == "neq":
            a, b = walk(goal[1], subst), walk(goal[2], subst)
            if not is_var(a) and not is_var(b) and a != b:
                yield from self._solve(rest, subst, depth)
            return
        for fact in self._facts.get(goal[0], ()):
            extended = unify(goal, fact, subst)
            if extended is not None:
                yield from self._solve(rest, extended, depth)
        if depth >= MAX_DEPTH:
            return
        for rule in self._rules.get(goal[0], ()):
            head, body = self._rename(rule)
            extended = unify(goal, head, subst)
            if extended is not None:
                yield from self._solve([*body, *rest], extended, depth + 1)
