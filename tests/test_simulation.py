"""Tests for the simulation loop, metrics, and configuration."""
import dataclasses

import numpy as np
import pytest

from infodemic.config import SimConfig, load_conditions, load_config, override
from infodemic.env.claims import ClaimView
from infodemic.env.simulation import Simulation, run_simulation
from infodemic.metrics import RoundStats, compute_metrics, paired_difference

CONFIG_DIR = "experiments/configs"


def stats(curve, takedowns=0, false_positives=0):
    return [RoundStats(i, n, 0, 0, takedowns, false_positives) for i, n in enumerate(curve)]


def test_same_seed_reproduces_the_run():
    cfg = SimConfig()
    a = run_simulation(cfg, "centrality", "impact_weighted", seed=7, shock=True).metrics
    b = run_simulation(cfg, "centrality", "impact_weighted", seed=7, shock=True).metrics
    assert a == b


def test_total_exposure_matches_exposed_users_on_false_claims():
    sim = Simulation(SimConfig(), "centrality", "fifo", seed=1, shock=True)
    result = sim.run()
    exposed = sum(
        1 for c in sim.claims.values() if c.is_false for n in c.exposed if not sim.net.is_bot(n)
    )
    assert result.metrics.total_exposure == exposed


def test_moderator_percepts_do_not_include_the_hidden_label():
    assert "is_false" not in {f.name for f in dataclasses.fields(ClaimView)}


def test_takedown_accounting():
    sim = Simulation(SimConfig(), "random", "impact_weighted", seed=2)
    sim.run()
    counted = [c for c in sim.claims.values() if c.takedown_counted]
    assert sim.takedowns == len(counted)
    assert sim.false_positives == sum(not c.is_false for c in counted)


def test_shock_raises_exposure_and_records_recovery():
    cfg = SimConfig()
    for seed in range(3):
        calm = run_simulation(cfg, "random", "fifo", seed).metrics
        shocked = run_simulation(cfg, "random", "fifo", seed, shock=True).metrics
        assert shocked.total_exposure > calm.total_exposure
        assert calm.recovery_time is None and shocked.recovery_time is not None


def test_spreader_deploys_sockpuppets_only_when_adaptive():
    adaptive = Simulation(SimConfig(), "centrality", "impact_weighted", seed=0)
    adaptive.run()
    fixed = Simulation(override(SimConfig(), {"spreader.max_sockpuppets": 0}), "centrality", "impact_weighted", seed=0)
    fixed.run()
    assert adaptive.spreader.sockpuppets and all(adaptive.net.is_bot(n) for n in adaptive.spreader.sockpuppets)
    assert not fixed.spreader.sockpuppets


def test_adaptation_does_not_hurt_the_spreader():
    def exposure(cfg):
        return sum(
            run_simulation(cfg, s, "impact_weighted", seed).metrics.total_exposure
            for s in ("random", "centrality")
            for seed in range(6)
        )

    assert exposure(SimConfig()) >= exposure(override(SimConfig(), {"spreader.max_sockpuppets": 0}))


def test_zero_budget_moderator_never_acts():
    cfg = override(SimConfig(), {"moderator.budget_per_round": 0})
    assert run_simulation(cfg, "random", "fifo", seed=0).metrics.takedowns == 0


def test_lower_lambda_takes_down_more_true_claims():
    seeds = range(8)
    def false_positives(lam):
        cfg = override(SimConfig(), {"moderator.lam": lam})
        return sum(run_simulation(cfg, "centrality", "impact_weighted", s).metrics.false_positives for s in seeds)

    assert false_positives(0.0) > false_positives(200.0)


def test_metrics_from_a_known_curve():
    m = compute_metrics(stats([5, 4, 3, 1, 0, 0], takedowns=4, false_positives=1), threshold=2)
    assert (m.total_exposure, m.peak_infection) == (13, 5)
    assert m.time_to_containment == 3 and m.contained
    assert m.false_positive_rate == 0.25 and m.recovery_time is None


def test_uncontained_run_is_censored_at_the_horizon():
    m = compute_metrics(stats([5, 5, 5, 5]), threshold=2)
    assert m.time_to_containment == 4 and not m.contained


def test_recovery_is_measured_from_the_shock_round():
    m = compute_metrics(stats([0, 0, 9, 8, 3, 0, 0]), threshold=2, shock_round=2)
    assert m.recovery_time == 3 and m.recovered


def test_paired_difference_detects_a_consistent_gap():
    rng = np.random.default_rng(0)
    mean, low, high = paired_difference(np.array([12, 15, 11, 14]), np.array([10, 10, 10, 10]), rng)
    assert mean == pytest.approx(3.0) and low > 0 and high >= mean


def test_default_config_files_load():
    cfg = load_config(f"{CONFIG_DIR}/default.yaml")
    assert cfg == dataclasses.replace(SimConfig(), seeds=tuple(range(30)))
    assert list(load_conditions(f"{CONFIG_DIR}/conditions.yaml")) == ["C1", "C2", "C3", "C4", "C5", "C6"]


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        override(SimConfig(), {"moderator.lam": -1})
    with pytest.raises(ValueError):
        override(SimConfig(), {"shock.round": 59})
