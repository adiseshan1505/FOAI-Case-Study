"""Coordinated bot-swarm shock: many spreader instances activate at a scheduled round."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from infodemic.agents.spreader import SpreaderAgent
from infodemic.config import ShockConfig, SpreaderConfig
from infodemic.policies.spreader_policies import SeedingPolicy

if TYPE_CHECKING:
    from infodemic.env.simulation import Simulation


class BotSwarm:
    """At the shock round, num_spreaders extra spreaders post simultaneously for `duration` rounds."""

    def __init__(self, shock: ShockConfig, spreader: SpreaderConfig, policy: SeedingPolicy, rng: np.random.Generator):
        self.shock = shock
        self.spreader = spreader
        self.policy = policy
        self.rng = rng
        self.agents: list[SpreaderAgent] = []

    def act(self, sim: Simulation, r: int) -> None:
        if r == self.shock.round:
            end = r + self.shock.duration
            self.agents = [
                SpreaderAgent(self.spreader, self.policy, self.rng, start=r, end=end, adaptive=False)
                for _ in range(self.shock.num_spreaders)
            ]
        for agent in self.agents:
            agent.act(sim, r)
