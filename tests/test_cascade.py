"""Tests for Independent Cascade dynamics."""
import networkx as nx
import numpy as np

from infodemic.env.cascade import cascade_step
from infodemic.env.claims import Claim, ClaimStatus, NodeState
from infodemic.env.network import Network


def make_claim(source: int = 0) -> Claim:
    claim = Claim(0, ("capital_of", "city_0", "country_0"), True, source, 0, 0.5, "test")
    claim.exposed, claim.frontier = {source}, [source]
    return claim


def path_network(n: int = 5, prob: float = 1.0) -> Network:
    return Network(nx.path_graph(n), [1.0] * n, prob, 1.0)


def test_certain_reshare_walks_the_path():
    net, claim, rng = path_network(), make_claim(), np.random.default_rng(0)
    counts = [cascade_step(net, claim, rng, 0.3) for _ in range(5)]
    assert counts == [1, 1, 1, 1, 0]
    assert claim.exposed == {0, 1, 2, 3, 4}


def test_zero_probability_never_spreads():
    net, claim = path_network(prob=1e-12), make_claim()
    assert cascade_step(net, claim, np.random.default_rng(0), 0.3) == 0
    assert claim.exposed == {0}


def test_each_node_gets_one_chance():
    net, claim, rng = path_network(3), make_claim(1), np.random.default_rng(0)
    cascade_step(net, claim, rng, 0.3)
    assert cascade_step(net, claim, rng, 0.3) == 0


def test_quarantine_stops_spread_and_blocks_frontier():
    net, claim = path_network(), make_claim()
    claim.blocked, claim.frontier, claim.status = {0}, [], ClaimStatus.QUARANTINED
    assert cascade_step(net, claim, np.random.default_rng(0), 0.3) == 0
    assert claim.node_state(0) is NodeState.QUARANTINED
    assert claim.node_state(3) is NodeState.CLEAN


def test_rate_limit_scales_reshare_probability():
    net, rng = path_network(2, prob=1.0), np.random.default_rng(0)
    spread = 0
    for _ in range(400):
        claim = make_claim()
        claim.status = ClaimStatus.RATE_LIMITED
        spread += cascade_step(net, claim, rng, 0.25)
    assert 60 < spread < 140


def test_sockpuppets_carry_claims_but_are_never_exposed():
    net = path_network(3)
    bot = net.add_sockpuppet([1])
    assert net.is_bot(bot) and not net.is_bot(1)
    claim = make_claim(0)
    claim.exposed.update({1})
    claim.frontier = [1]
    cascade_step(net, claim, np.random.default_rng(0), 0.3)
    assert bot not in claim.exposed
