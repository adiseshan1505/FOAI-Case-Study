"""Run metrics: total exposure, peak infection, time-to-containment, false-positive rate, post-shock recovery time."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class RoundStats:
    round: int
    new_false_exposures: int
    active_false_claims: int
    queue_len: int
    takedowns: int
    false_positives: int


@dataclass(frozen=True)
class RunMetrics:
    total_exposure: int
    peak_infection: int
    time_to_containment: int
    contained: bool
    false_positives: int
    takedowns: int
    false_positive_rate: float
    recovery_time: int | None
    recovered: bool | None

    def objective(self, lam: float) -> float:
        return self.total_exposure + lam * self.false_positives

    def as_dict(self) -> dict:
        return asdict(self)


def _settling_time(curve: np.ndarray, threshold: int) -> tuple[int, bool]:
    """Rounds until the curve stays at or below threshold, and whether it does so by the end."""
    above = np.flatnonzero(curve > threshold)
    if len(above) == 0:
        return 0, True
    last = int(above[-1])
    return last + 1, last < len(curve) - 1


def compute_metrics(stats: list[RoundStats], threshold: int, shock_round: int | None = None) -> RunMetrics:
    """The infection curve is the number of users newly exposed to false claims each round."""
    curve = np.array([s.new_false_exposures for s in stats])
    ttc, contained = _settling_time(curve, threshold)
    recovery = recovered = None
    if shock_round is not None:
        recovery, recovered = _settling_time(curve[shock_round:], threshold)
    takedowns, false_positives = stats[-1].takedowns, stats[-1].false_positives
    return RunMetrics(
        total_exposure=int(curve.sum()),
        peak_infection=int(curve.max()),
        time_to_containment=ttc,
        contained=contained,
        false_positives=false_positives,
        takedowns=takedowns,
        false_positive_rate=false_positives / takedowns if takedowns else 0.0,
        recovery_time=recovery,
        recovered=recovered,
    )


def paired_difference(
    a: np.ndarray, b: np.ndarray, rng: np.random.Generator, n_boot: int = 5000
) -> tuple[float, float, float]:
    """Mean of a - b with a 95% bootstrap confidence interval; a and b are paired by seed."""
    diffs = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    boots = rng.choice(diffs, size=(n_boot, len(diffs)), replace=True).mean(axis=1)
    low, high = np.percentile(boots, [2.5, 97.5])
    return float(diffs.mean()), float(low), float(high)
