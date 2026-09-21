"""Scale-free graph construction, node states (clean, exposed, quarantined), and edge reshare probabilities."""
from __future__ import annotations

from collections.abc import Iterable

import networkx as nx
import numpy as np

from infodemic.config import GraphConfig


class Network:
    """Static scale-free graph of ordinary users. Sockpuppets are the only nodes added later.

    Nodes 0..num_humans-1 are ordinary users; anything above is a sockpuppet
    that can carry a claim but never counts as an exposed user.
    """

    def __init__(self, graph: nx.Graph, trust: Iterable[float], base_prob: float, sockpuppet_trust: float):
        self.graph = graph
        self.num_humans = graph.number_of_nodes()
        self._trust = list(trust)
        self._base_prob = base_prob
        self._sockpuppet_trust = sockpuppet_trust
        degrees = np.array([graph.degree(n) for n in range(self.num_humans)])
        self._hub_order = np.argsort(-degrees, kind="stable").tolist()

    def is_bot(self, node: int) -> bool:
        return node >= self.num_humans

    def neighbors(self, node: int):
        return self.graph.adj[node]

    def degree(self, node: int) -> int:
        return self.graph.degree(node)

    def edge_prob(self, u: int, v: int) -> float:
        return min(1.0, self._base_prob * self._trust[u])

    def hubs(self, fraction: float) -> list[int]:
        return self._hub_order[: max(1, int(fraction * self.num_humans))]

    def add_sockpuppet(self, targets: Iterable[int]) -> int:
        node = self.graph.number_of_nodes()
        self.graph.add_node(node)
        self.graph.add_edges_from((node, t) for t in targets)
        self._trust.append(self._sockpuppet_trust)
        return node


def build_network(cfg: GraphConfig, rng: np.random.Generator) -> Network:
    graph = nx.barabasi_albert_graph(cfg.num_nodes, cfg.attachment_edges, seed=int(rng.integers(2**31)))
    trust = rng.uniform(*cfg.trust_range, size=cfg.num_nodes)
    return Network(graph, trust, cfg.base_reshare_prob, cfg.sockpuppet_trust)
