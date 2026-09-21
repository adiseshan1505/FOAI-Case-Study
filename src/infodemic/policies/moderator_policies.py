"""Moderator claim-selection policies: random, FIFO, and impact-weighted."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from infodemic.env.claims import ClaimView


class ModeratorPolicy(Protocol):
    def select(self, queue: Sequence[ClaimView], budget: int, rng: np.random.Generator) -> list[ClaimView]: ...


class RandomModeration:
    def select(self, queue: Sequence[ClaimView], budget: int, rng: np.random.Generator) -> list[ClaimView]:
        order = rng.permutation(len(queue))[:budget]
        return [queue[i] for i in order]


class FIFOModeration:
    def select(self, queue: Sequence[ClaimView], budget: int, rng: np.random.Generator) -> list[ClaimView]:
        return sorted(queue, key=lambda v: (v.created_round, v.id))[:budget]


class ImpactWeightedModeration:
    """Ranks claims by impact (velocity x reach of current carriers), weighted by suspicion.

    With use_suspicion=False it ranks by velocity x reach alone, as in the
    problem statement. With refresh=False the score is frozen when a claim is
    first seen, which models a static queue that ignores how the spread evolves.
    """

    def __init__(self, refresh: bool = True, use_suspicion: bool = True):
        self.refresh = refresh
        self.use_suspicion = use_suspicion
        self._frozen: dict[int, float] = {}

    def _score(self, view: ClaimView) -> float:
        return view.impact * (view.p_false if self.use_suspicion else 1.0)

    def select(self, queue: Sequence[ClaimView], budget: int, rng: np.random.Generator) -> list[ClaimView]:
        scores = {}
        for view in queue:
            if self.refresh:
                scores[view.id] = self._score(view)
            else:
                scores[view.id] = self._frozen.setdefault(view.id, self._score(view))
        tie_break = (lambda v: -v.p_false) if self.use_suspicion else (lambda v: 0.0)
        ranked = sorted(queue, key=lambda v: (-scores[v.id], tie_break(v), v.id))
        return ranked[:budget]


def make_moderator_policy(name: str) -> ModeratorPolicy:
    factories = {
        "random": RandomModeration,
        "fifo": FIFOModeration,
        "impact_weighted": ImpactWeightedModeration,
        "impact_only": lambda: ImpactWeightedModeration(use_suspicion=False),
        "impact_static": lambda: ImpactWeightedModeration(refresh=False),
    }
    if name not in factories:
        raise ValueError(f"unknown moderator policy: {name!r}; choose from {sorted(factories)}")
    return factories[name]()
