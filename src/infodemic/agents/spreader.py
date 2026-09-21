"""Spreader agent: post, reshare, create sockpuppets, target hubs."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from infodemic.config import SpreaderConfig
from infodemic.env.claims import ClaimStatus
from infodemic.policies.spreader_policies import SeedingPolicy

if TYPE_CHECKING:
    from infodemic.env.simulation import Simulation

ALARM_MEMORY = 3


class SpreaderAgent:
    """Posts false claims and reacts to visible moderator activity.

    The spreader sees only the public log of suppressions. When one of its own
    claims was suppressed recently it becomes alarmed: it deploys sockpuppets,
    posts from those fresh identities, and has them reshare its strongest claim.
    """

    def __init__(
        self,
        cfg: SpreaderConfig,
        policy: SeedingPolicy,
        rng: np.random.Generator,
        start: int = 0,
        end: int | None = None,
        adaptive: bool = True,
    ):
        self.cfg = cfg
        self.policy = policy
        self.rng = rng
        self.start = start
        self.end = cfg.campaign_rounds if end is None else end
        self.adaptive = adaptive
        self.claim_ids: list[int] = []
        self.sockpuppets: list[int] = []
        self._uses: dict[int, int] = {}

    def act(self, sim: Simulation, r: int) -> None:
        if not self.start <= r < self.end:
            return
        alarmed = self.adaptive and self._alarmed(sim, r)
        if alarmed:
            self._deploy_sockpuppets(sim)
        for _ in range(self.cfg.posts_per_round):
            claim = sim.post_claim(self._pick_source(sim, alarmed), True, "spreader", self.rng)
            self.claim_ids.append(claim.id)
        if alarmed:
            self._reshare(sim)

    def _alarmed(self, sim: Simulation, r: int) -> bool:
        return bool(sim.recent_suppressions(r - ALARM_MEMORY) & set(self.claim_ids))

    def _deploy_sockpuppets(self, sim: Simulation) -> None:
        room = self.cfg.max_sockpuppets - len(self.sockpuppets)
        for _ in range(min(self.cfg.sockpuppets_per_round, room)):
            links = self.policy.pick(sim.net, self.cfg.sockpuppet_links, self.rng)
            self.sockpuppets.append(sim.net.add_sockpuppet(links))

    def _pick_source(self, sim: Simulation, alarmed: bool) -> int:
        if alarmed and self.sockpuppets:
            node = min(self.sockpuppets, key=lambda n: self._uses.get(n, 0))
            self._uses[node] = self._uses.get(node, 0) + 1
            return node
        return self.policy.pick(sim.net, 1, self.rng)[0]

    def _reshare(self, sim: Simulation) -> None:
        views = [sim.view(cid) for cid in self.claim_ids]
        live = [v for v in views if v.status is not ClaimStatus.QUARANTINED]
        if not live:
            return
        target = max(live, key=lambda v: v.exposed_count)
        for node in self.sockpuppets:
            sim.reshare(target.id, node)
