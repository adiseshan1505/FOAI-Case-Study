"""Independent Cascade dynamics for claim propagation."""
from __future__ import annotations

import numpy as np

from infodemic.env.claims import Claim
from infodemic.env.network import Network


def cascade_step(net: Network, claim: Claim, rng: np.random.Generator, rate_limit_factor: float) -> int:
    """Advance one Independent Cascade hop and return the number of newly exposed users.

    Every node in the frontier gets a single chance to pass the claim to each
    neighbor. Rate limiting scales the reshare probability; quarantine stops it.
    """
    factor = claim.spread_factor(rate_limit_factor)
    if factor == 0.0 or not claim.frontier:
        claim.frontier = []
        return 0
    newly_exposed: list[int] = []
    for u in claim.frontier:
        for v in net.neighbors(u):
            if v in claim.exposed or net.is_bot(v):
                continue
            if rng.random() < net.edge_prob(u, v) * factor:
                claim.exposed.add(v)
                newly_exposed.append(v)
    claim.frontier = newly_exposed
    return len(newly_exposed)
