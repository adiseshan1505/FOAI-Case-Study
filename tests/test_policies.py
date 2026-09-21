"""Tests for spreader and moderator policies."""
import numpy as np
import pytest

from infodemic.config import GraphConfig, SpreaderConfig
from infodemic.env.claims import ClaimStatus, ClaimView
from infodemic.env.network import build_network
from infodemic.policies.moderator_policies import (
    FIFOModeration,
    ImpactWeightedModeration,
    RandomModeration,
    make_moderator_policy,
)
from infodemic.policies.spreader_policies import CentralitySeeding, RandomSeeding, make_seeding_policy


def view(id_, created=0, velocity=1, reach=1, p_false=0.5) -> ClaimView:
    return ClaimView(id_, ("x",), 0, created, 0.5, ClaimStatus.ACTIVE, velocity, reach, 0.0, 1, p_false)


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def test_fifo_orders_by_arrival():
    queue = [view(2, created=5), view(0, created=1), view(1, created=1)]
    assert [v.id for v in FIFOModeration().select(queue, 2, None)] == [0, 1]


def test_random_moderation_respects_budget(rng):
    queue = [view(i) for i in range(10)]
    chosen = RandomModeration().select(queue, 3, rng)
    assert len(chosen) == 3 and len({v.id for v in chosen}) == 3
    assert RandomModeration().select([], 3, rng) == []


def test_impact_weighted_ranks_by_velocity_times_reach(rng):
    queue = [view(0, velocity=1, reach=100), view(1, velocity=10, reach=50), view(2, velocity=2, reach=10)]
    assert [v.id for v in ImpactWeightedModeration().select(queue, 2, rng)] == [1, 0]


def test_suspicion_breaks_impact_ties(rng):
    queue = [view(0, reach=10, p_false=0.2), view(1, reach=10, p_false=0.9)]
    assert ImpactWeightedModeration().select(queue, 1, rng)[0].id == 1


def test_static_ranking_ignores_later_changes(rng):
    static, adaptive = ImpactWeightedModeration(refresh=False), ImpactWeightedModeration()
    before = [view(0, reach=100), view(1, reach=10)]
    after = [view(0, reach=1), view(1, reach=500)]
    assert static.select(before, 1, rng)[0].id == adaptive.select(before, 1, rng)[0].id == 0
    assert static.select(after, 1, rng)[0].id == 0
    assert adaptive.select(after, 1, rng)[0].id == 1


def test_seeding_policies(rng):
    net = build_network(GraphConfig(num_nodes=200), rng)
    hubs = set(net.hubs(0.05))
    picked = CentralitySeeding(0.05).pick(net, 5, rng)
    assert set(picked) <= hubs and len(set(picked)) == 5
    assert len(set(RandomSeeding().pick(net, 20, rng))) == 20


def test_centrality_seeds_have_higher_degree_than_random(rng):
    net = build_network(GraphConfig(num_nodes=500), rng)
    hub = np.mean([net.degree(n) for n in CentralitySeeding(0.05).pick(net, 20, rng)])
    rand = np.mean([net.degree(n) for n in RandomSeeding().pick(net, 20, rng)])
    assert hub > 2 * rand


def test_unknown_policy_names_are_rejected():
    with pytest.raises(ValueError):
        make_moderator_policy("nope")
    with pytest.raises(ValueError):
        make_seeding_policy("nope", SpreaderConfig())
