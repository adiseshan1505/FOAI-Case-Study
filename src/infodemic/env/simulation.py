"""Round-by-round simulation loop coordinating the environment and both agents."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from infodemic.agents.moderator import Moderator
from infodemic.agents.spreader import SpreaderAgent
from infodemic.config import SimConfig
from infodemic.env.cascade import cascade_step
from infodemic.env.claims import Claim, ClaimFactory, ClaimStatus, ClaimView
from infodemic.env.network import build_network
from infodemic.kb.facts import generate_world, sample_kb_facts
from infodemic.kb.inference import KnowledgeBase
from infodemic.kb.rules import RULES
from infodemic.metrics import RoundStats, RunMetrics, compute_metrics
from infodemic.policies.moderator_policies import make_moderator_policy
from infodemic.policies.spreader_policies import make_seeding_policy
from infodemic.scenarios.bot_swarm import BotSwarm

STREAMS = ("graph", "world", "organic", "spreader", "moderator", "cascade", "swarm", "review")


@dataclass(frozen=True)
class RunResult:
    metrics: RunMetrics
    stats: list[RoundStats]


class Simulation:
    """One episode. Each component draws from its own seeded random stream, so runs
    with the same seed share the same graph, knowledge base and organic claims
    regardless of which policies are being compared."""

    def __init__(self, cfg: SimConfig, spreader_policy: str, moderator_policy: str, seed: int, shock: bool = False):
        seeds = np.random.SeedSequence(seed).spawn(len(STREAMS))
        self.rngs = {name: np.random.default_rng(s) for name, s in zip(STREAMS, seeds)}
        self.cfg = cfg
        self.shock = shock
        self.net = build_network(cfg.graph, self.rngs["graph"])
        world = generate_world(self.rngs["world"])
        kb = KnowledgeBase(sample_kb_facts(world, cfg.moderator.kb_coverage, self.rngs["world"]), RULES)
        self.factory = ClaimFactory(world, cfg.claims.evidence_noise)
        seeding = make_seeding_policy(spreader_policy, cfg.spreader)
        self.spreader = SpreaderAgent(cfg.spreader, seeding, self.rngs["spreader"])
        self.swarm = BotSwarm(cfg.shock, cfg.spreader, seeding, self.rngs["swarm"]) if shock else None
        self.moderator = Moderator(cfg.moderator, kb, make_moderator_policy(moderator_policy), self.rngs["moderator"])
        self.claims: dict[int, Claim] = {}
        self.round = 0
        self.stats: list[RoundStats] = []
        self.takedowns = 0
        self.false_positives = 0
        self._created: dict[int, list[int]] = defaultdict(list)
        self._suppressions: list[tuple[int, int]] = []
        self._incidence = 0

    def step(self) -> None:
        r = self.round
        self._incidence = 0
        self.spreader.act(self, r)
        if self.swarm:
            self.swarm.act(self, r)
        self._post_organic(r)
        self.moderator.act(self, r)
        for claim in self.claims.values():
            new = cascade_step(self.net, claim, self.rngs["cascade"], self.cfg.moderator.rate_limit_factor)
            if claim.is_false:
                self._incidence += new
        self.stats.append(self._snapshot(r))
        self.round += 1

    def run(self) -> RunResult:
        while self.round < self.cfg.horizon:
            self.step()
        shock_round = self.cfg.shock.round if self.shock else None
        return RunResult(compute_metrics(self.stats, self.cfg.containment_threshold, shock_round), self.stats)

    def post_claim(self, source: int, is_false: bool, origin: str, rng: np.random.Generator) -> Claim:
        claim = self.factory.make(source, self.round, is_false, origin, rng)
        claim.exposed.add(source)
        claim.frontier.append(source)
        self.claims[claim.id] = claim
        self._created[self.round].append(claim.id)
        if is_false and not self.net.is_bot(source):
            self._incidence += 1
        return claim

    def reshare(self, claim_id: int, node: int) -> None:
        claim = self.claims[claim_id]
        if claim.status is not ClaimStatus.QUARANTINED and node not in claim.frontier:
            claim.frontier.append(node)

    def view(self, claim_id: int) -> ClaimView:
        return self.claims[claim_id].view(self.net, self.cfg.moderator.rate_limit_factor)

    def claims_created_at(self, r: int) -> list[int]:
        return list(self._created.get(r, ()))

    def recent_suppressions(self, since: int) -> set[int]:
        return {cid for when, cid in self._suppressions if when >= since}

    def suppress(self, claim_id: int, status: ClaimStatus, r: int) -> None:
        claim = self.claims[claim_id]
        if claim.status is ClaimStatus.QUARANTINED or claim.status is status:
            return
        if status is ClaimStatus.QUARANTINED:
            claim.blocked = set(claim.frontier)
            claim.frontier = []
        claim.status = status
        if not claim.takedown_counted:
            claim.takedown_counted = True
            self.takedowns += 1
            self.false_positives += not claim.is_false
        self._suppressions.append((r, claim_id))

    def release(self, claim_id: int) -> None:
        claim = self.claims[claim_id]
        if claim.status is ClaimStatus.RATE_LIMITED:
            claim.status = ClaimStatus.ACTIVE

    def human_review(self, claim_id: int, accuracy: float) -> bool:
        """Slow human review: returns whether the claim is false, correct with probability `accuracy`."""
        truth = self.claims[claim_id].is_false
        return truth if self.rngs["review"].random() < accuracy else not truth

    def _post_organic(self, r: int) -> None:
        rng = self.rngs["organic"]
        for _ in range(rng.poisson(self.cfg.claims.organic_rate)):
            is_false = bool(rng.random() < self.cfg.claims.organic_false_prob)
            self.post_claim(int(rng.integers(self.net.num_humans)), is_false, "organic", rng)

    def _snapshot(self, r: int) -> RoundStats:
        return RoundStats(
            round=r,
            new_false_exposures=self._incidence,
            active_false_claims=sum(1 for c in self.claims.values() if c.is_false and c.frontier),
            queue_len=len(self.moderator.queue),
            takedowns=self.takedowns,
            false_positives=self.false_positives,
        )


def run_simulation(cfg: SimConfig, spreader: str, moderator: str, seed: int, shock: bool = False) -> RunResult:
    return Simulation(cfg, spreader, moderator, seed, shock).run()
