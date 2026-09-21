"""Moderator agent: flag claims, verify them against the knowledge base, quarantine or rate-limit, escalate."""
from __future__ import annotations

import math
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from infodemic.config import ModeratorConfig
from infodemic.env.claims import ClaimStatus, ClaimView
from infodemic.kb.inference import KnowledgeBase, Verdict
from infodemic.policies.moderator_policies import ModeratorPolicy

if TYPE_CHECKING:
    from infodemic.env.simulation import Simulation

CONTENT_WEIGHT = 8.0
CONTENT_MIDPOINT = 0.525
SOURCE_WEIGHT = 3.0


class Moderator:
    """Verifies up to B queued claims per round against the knowledge base.

    A FALSE verdict quarantines the claim. When the knowledge base cannot
    resolve a claim, the moderator weighs the expected exposure it would
    prevent against lambda times the chance of suppressing true content, and
    may rate-limit provisionally and/or escalate to slow human review.
    """

    def __init__(self, cfg: ModeratorConfig, kb: KnowledgeBase, policy: ModeratorPolicy, rng: np.random.Generator):
        self.cfg = cfg
        self.kb = kb
        self.policy = policy
        self.rng = rng
        self.queue: list[int] = []
        self.ledger: dict[int, list[int]] = {}
        self.reviews: list[tuple[int, int]] = []

    def act(self, sim: Simulation, r: int) -> None:
        self.queue.extend(sim.claims_created_at(r - self.cfg.detection_delay))
        self._resolve_reviews(sim, r)
        views = [self._annotate(sim.view(cid)) for cid in self.queue]
        views = [v for v in views if r - v.created_round <= self.cfg.queue_ttl]
        self.queue = [v.id for v in views]
        for view in self.policy.select(views, self.cfg.budget_per_round, self.rng):
            self._verify(sim, view, r)

    def _annotate(self, view: ClaimView) -> ClaimView:
        bad, good = self.ledger.get(view.source, (0, 0))
        suspicion = (bad + 1) / (bad + good + 2)
        z = CONTENT_WEIGHT * (view.content_score - CONTENT_MIDPOINT) + SOURCE_WEIGHT * (suspicion - 0.5)
        return replace(view, p_false=1.0 / (1.0 + math.exp(-z)))

    def _record(self, source: int, is_false: bool) -> None:
        self.ledger.setdefault(source, [0, 0])[0 if is_false else 1] += 1

    def _verify(self, sim: Simulation, view: ClaimView, r: int) -> None:
        self.queue.remove(view.id)
        verdict = self.kb.verify(view.atom)
        if verdict is Verdict.UNKNOWN:
            self._handle_unknown(sim, view, r)
            return
        self._record(view.source, verdict is Verdict.FALSE)
        if verdict is Verdict.FALSE:
            sim.suppress(view.id, ClaimStatus.QUARANTINED, r)

    def _handle_unknown(self, sim: Simulation, view: ClaimView, r: int) -> None:
        cfg = self.cfg
        if cfg.unknown_policy == "adaptive":
            harm = view.p_false * view.expected_next * cfg.lookahead
            limit = harm * (1 - cfg.rate_limit_factor) > cfg.lam * (1 - view.p_false)
            escalate = harm >= cfg.escalate_threshold
        else:
            limit = cfg.unknown_policy == "rate_limit"
            escalate = cfg.unknown_policy == "escalate"
        if limit:
            sim.suppress(view.id, ClaimStatus.RATE_LIMITED, r)
        if escalate and len(self.reviews) < cfg.escalation_capacity:
            self.reviews.append((r + cfg.escalation_delay, view.id))

    def _resolve_reviews(self, sim: Simulation, r: int) -> None:
        due = [cid for when, cid in self.reviews if when <= r]
        self.reviews = [(when, cid) for when, cid in self.reviews if when > r]
        for cid in due:
            is_false = sim.human_review(cid, self.cfg.escalation_accuracy)
            self._record(sim.view(cid).source, is_false)
            if is_false:
                sim.suppress(cid, ClaimStatus.QUARANTINED, r)
            else:
                sim.release(cid)
