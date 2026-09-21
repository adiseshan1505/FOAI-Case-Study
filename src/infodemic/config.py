"""Loads and validates experiment configuration (graph size, budget B, lambda, horizon T, shock round)."""
from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass, field
from pathlib import Path

import yaml

UNKNOWN_POLICIES = ("adaptive", "rate_limit", "escalate", "ignore")


@dataclass(frozen=True)
class GraphConfig:
    num_nodes: int = 750
    attachment_edges: int = 3
    base_reshare_prob: float = 0.1
    trust_range: tuple[float, float] = (0.6, 1.4)
    sockpuppet_trust: float = 1.0


@dataclass(frozen=True)
class SpreaderConfig:
    posts_per_round: int = 3
    campaign_rounds: int = 20
    sockpuppets_per_round: int = 1
    max_sockpuppets: int = 10
    sockpuppet_links: int = 8
    hub_fraction: float = 0.05


@dataclass(frozen=True)
class ModeratorConfig:
    budget_per_round: int = 2
    lam: float = 10.0
    detection_delay: int = 1
    rate_limit_factor: float = 0.3
    kb_coverage: float = 0.7
    queue_ttl: int = 25
    unknown_policy: str = "adaptive"
    lookahead: float = 3.0
    escalate_threshold: float = 1.0
    escalation_capacity: int = 2
    escalation_delay: int = 3
    escalation_accuracy: float = 0.95


@dataclass(frozen=True)
class ClaimConfig:
    organic_rate: float = 1.0
    organic_false_prob: float = 0.1
    evidence_noise: float = 0.15


@dataclass(frozen=True)
class ShockConfig:
    round: int = 30
    num_spreaders: int = 12
    duration: int = 3


@dataclass(frozen=True)
class SimConfig:
    horizon: int = 60
    containment_threshold: int = 2
    graph: GraphConfig = field(default_factory=GraphConfig)
    spreader: SpreaderConfig = field(default_factory=SpreaderConfig)
    moderator: ModeratorConfig = field(default_factory=ModeratorConfig)
    claims: ClaimConfig = field(default_factory=ClaimConfig)
    shock: ShockConfig = field(default_factory=ShockConfig)
    seeds: tuple[int, ...] = tuple(range(10))


def _build(cls, data: dict):
    hints = typing.get_type_hints(cls)
    unknown = set(data) - set(hints)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} keys: {sorted(unknown)}")
    kwargs = {}
    for name, value in data.items():
        hint = hints[name]
        if dataclasses.is_dataclass(hint):
            value = _build(hint, value or {})
        elif typing.get_origin(hint) is tuple:
            value = tuple(value)
        kwargs[name] = value
    return cls(**kwargs)


def validate(cfg: SimConfig) -> SimConfig:
    g, s, m, c, k = cfg.graph, cfg.spreader, cfg.moderator, cfg.claims, cfg.shock
    checks = [
        (g.num_nodes > g.attachment_edges >= 1, "graph.attachment_edges must be in [1, num_nodes)"),
        (0 < g.base_reshare_prob <= 1, "graph.base_reshare_prob must be in (0, 1]"),
        (0 < g.trust_range[0] <= g.trust_range[1], "graph.trust_range must be an ascending positive pair"),
        (s.posts_per_round >= 0 and s.sockpuppets_per_round >= 0, "spreader budgets must be non-negative"),
        (0 < s.hub_fraction <= 1, "spreader.hub_fraction must be in (0, 1]"),
        (m.budget_per_round >= 0 and m.lam >= 0, "moderator.budget_per_round and lam must be non-negative"),
        (0 <= m.rate_limit_factor <= 1, "moderator.rate_limit_factor must be in [0, 1]"),
        (0 <= m.kb_coverage <= 1, "moderator.kb_coverage must be in [0, 1]"),
        (m.unknown_policy in UNKNOWN_POLICIES, f"moderator.unknown_policy must be one of {UNKNOWN_POLICIES}"),
        (0 <= c.organic_false_prob <= 1 and c.organic_rate >= 0, "invalid claims settings"),
        (0 <= k.round and k.round + k.duration <= cfg.horizon, "shock must fit inside the horizon"),
        (len(cfg.seeds) > 0, "seeds must not be empty"),
    ]
    for ok, message in checks:
        if not ok:
            raise ValueError(message)
    return cfg


def load_config(path: str | Path) -> SimConfig:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return validate(_build(SimConfig, data))


def load_conditions(path: str | Path) -> dict[str, tuple[str, str]]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return {name: (c["spreader"], c["moderator"]) for name, c in data["conditions"].items()}


def override(cfg: SimConfig, updates: dict[str, object]) -> SimConfig:
    """Return a copy of cfg with dotted-path updates applied, e.g. {"moderator.lam": 5}."""

    def set_path(obj, parts, value):
        head, *rest = parts
        new = set_path(getattr(obj, head), rest, value) if rest else value
        return dataclasses.replace(obj, **{head: new})

    for path, value in updates.items():
        cfg = set_path(cfg, path.split("."), value)
    return validate(cfg)
