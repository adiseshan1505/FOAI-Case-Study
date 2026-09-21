"""Hand-authored facts for claim verification."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from infodemic.kb.inference import Atom

CLAIM_KINDS = ("capital_of", "located_in", "allied")


@dataclass(frozen=True)
class World:
    """Synthetic ground truth: every country has one capital, one region and one bloc."""

    countries: tuple[str, ...]
    cities: tuple[str, ...]
    regions: tuple[str, ...]
    blocs: tuple[str, ...]
    region_of: tuple[int, ...]
    bloc_of: tuple[int, ...]

    def base_facts(self) -> list[Atom]:
        facts: list[Atom] = []
        for i, (country, city) in enumerate(zip(self.countries, self.cities)):
            facts.append(("capital_of", city, country))
            facts.append(("part_of", country, self.regions[self.region_of[i]]))
            facts.append(("member_of", country, self.blocs[self.bloc_of[i]]))
        return facts

    def true_atom(self, rng: np.random.Generator) -> Atom:
        kind = CLAIM_KINDS[int(rng.integers(len(CLAIM_KINDS)))]
        i = int(rng.integers(len(self.countries)))
        if kind == "capital_of":
            return ("capital_of", self.cities[i], self.countries[i])
        if kind == "located_in":
            return ("located_in", self.cities[i], self.regions[self.region_of[i]])
        peers = [j for j in range(len(self.countries)) if j != i and self.bloc_of[j] == self.bloc_of[i]]
        if not peers:
            return self.true_atom(rng)
        return ("allied", self.countries[i], self.countries[peers[int(rng.integers(len(peers)))]])

    def false_atom(self, rng: np.random.Generator) -> Atom:
        kind = CLAIM_KINDS[int(rng.integers(len(CLAIM_KINDS)))]
        i = int(rng.integers(len(self.countries)))
        if kind == "capital_of":
            others = [j for j in range(len(self.countries)) if j != i]
            return ("capital_of", self.cities[i], self.countries[others[int(rng.integers(len(others)))]])
        if kind == "located_in":
            others = [r for r in range(len(self.regions)) if r != self.region_of[i]]
            return ("located_in", self.cities[i], self.regions[others[int(rng.integers(len(others)))]])
        rivals = [j for j in range(len(self.countries)) if self.bloc_of[j] != self.bloc_of[i]]
        return ("allied", self.countries[i], self.countries[rivals[int(rng.integers(len(rivals)))]])


def generate_world(
    rng: np.random.Generator, n_countries: int = 40, n_regions: int = 5, n_blocs: int = 6
) -> World:
    if n_regions < 2 or n_blocs < 2:
        raise ValueError("need at least two regions and two blocs to build false claims")
    return World(
        countries=tuple(f"country_{i}" for i in range(n_countries)),
        cities=tuple(f"city_{i}" for i in range(n_countries)),
        regions=tuple(f"region_{i}" for i in range(n_regions)),
        blocs=tuple(f"bloc_{i}" for i in range(n_blocs)),
        region_of=tuple(int(x) for x in rng.integers(n_regions, size=n_countries)),
        bloc_of=tuple(int(x) for x in rng.integers(n_blocs, size=n_countries)),
    )


def sample_kb_facts(world: World, coverage: float, rng: np.random.Generator) -> list[Atom]:
    """The moderator's knowledge base holds only a random subset of the world's base facts."""
    facts = world.base_facts()
    keep = rng.random(len(facts)) < coverage
    return [fact for fact, kept in zip(facts, keep) if kept]
