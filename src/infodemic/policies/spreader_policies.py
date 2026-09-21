"""Spreader seeding policies: random and centrality-informed."""
from __future__ import annotations

from typing import Protocol

import numpy as np

from infodemic.config import SpreaderConfig
from infodemic.env.network import Network


class SeedingPolicy(Protocol):
    def pick(self, net: Network, k: int, rng: np.random.Generator) -> list[int]: ...


class RandomSeeding:
    def pick(self, net: Network, k: int, rng: np.random.Generator) -> list[int]:
        return [int(n) for n in rng.choice(net.num_humans, size=k, replace=False)]


class CentralitySeeding:
    """Seeds from the top hub_fraction of nodes by degree centrality."""

    def __init__(self, hub_fraction: float):
        self.hub_fraction = hub_fraction

    def pick(self, net: Network, k: int, rng: np.random.Generator) -> list[int]:
        pool = net.hubs(self.hub_fraction)
        return [int(n) for n in rng.choice(pool, size=min(k, len(pool)), replace=False)]


def make_seeding_policy(name: str, cfg: SpreaderConfig) -> SeedingPolicy:
    if name == "random":
        return RandomSeeding()
    if name == "centrality":
        return CentralitySeeding(cfg.hub_fraction)
    raise ValueError(f"unknown spreader policy: {name!r}")
