"""Synthetic predicate claims with hidden true/false labels and noisy evidence."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from infodemic.env.network import Network
from infodemic.kb.facts import World
from infodemic.kb.inference import Atom

FALSE_SCORE_MEAN = 0.65
TRUE_SCORE_MEAN = 0.40


class ClaimStatus(Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    QUARANTINED = "quarantined"


class NodeState(Enum):
    CLEAN = "clean"
    EXPOSED = "exposed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class ClaimView:
    """What the moderator can observe about a claim. The hidden label is not included."""

    id: int
    atom: Atom
    source: int
    created_round: int
    content_score: float
    status: ClaimStatus
    velocity: int
    reach: int
    expected_next: float
    exposed_count: int
    p_false: float = 0.5

    @property
    def impact(self) -> float:
        return float(self.velocity * self.reach)


@dataclass
class Claim:
    id: int
    atom: Atom
    is_false: bool
    source: int
    created_round: int
    content_score: float
    origin: str
    status: ClaimStatus = ClaimStatus.ACTIVE
    exposed: set[int] = field(default_factory=set)
    frontier: list[int] = field(default_factory=list)
    blocked: set[int] = field(default_factory=set)
    takedown_counted: bool = False

    def node_state(self, node: int) -> NodeState:
        if node in self.blocked:
            return NodeState.QUARANTINED
        return NodeState.EXPOSED if node in self.exposed else NodeState.CLEAN

    def spread_factor(self, rate_limit_factor: float) -> float:
        if self.status is ClaimStatus.QUARANTINED:
            return 0.0
        return rate_limit_factor if self.status is ClaimStatus.RATE_LIMITED else 1.0

    def view(self, net: Network, rate_limit_factor: float) -> ClaimView:
        factor = self.spread_factor(rate_limit_factor)
        expected = sum(
            net.edge_prob(u, v) * factor
            for u in self.frontier
            for v in net.neighbors(u)
            if v not in self.exposed and not net.is_bot(v)
        )
        return ClaimView(
            id=self.id,
            atom=self.atom,
            source=self.source,
            created_round=self.created_round,
            content_score=self.content_score,
            status=self.status,
            velocity=len(self.frontier),
            reach=sum(net.degree(u) for u in self.frontier),
            expected_next=expected,
            exposed_count=len(self.exposed),
        )


class ClaimFactory:
    def __init__(self, world: World, noise: float):
        self.world = world
        self.noise = noise
        self._next_id = 0

    def make(self, source: int, round_: int, is_false: bool, origin: str, rng: np.random.Generator) -> Claim:
        atom = self.world.false_atom(rng) if is_false else self.world.true_atom(rng)
        mean = FALSE_SCORE_MEAN if is_false else TRUE_SCORE_MEAN
        score = float(np.clip(rng.normal(mean, self.noise), 0.0, 1.0))
        claim = Claim(self._next_id, atom, is_false, source, round_, score, origin)
        self._next_id += 1
        return claim
