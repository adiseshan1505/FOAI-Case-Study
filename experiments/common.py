"""Shared helpers for the experiment runners: run collection, CLI arguments, and chart styling."""
from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from infodemic.config import SimConfig, load_config
from infodemic.env.simulation import run_simulation

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "experiments" / "configs"
RESULTS_DIR = ROOT / "results"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MODERATOR_COLORS = {
    "random": BLUE,
    "fifo": ORANGE,
    "impact_weighted": AQUA,
    "impact_only": AQUA,
    "impact_static": AQUA,
}
MODERATOR_LABELS = {
    "random": "Random",
    "fifo": "FIFO",
    "impact_weighted": "Impact-weighted",
    "impact_only": "Impact only (no suspicion)",
    "impact_static": "Impact-weighted (static)",
}
SPREADER_LABELS = {"random": "Random targeting", "centrality": "Centrality-informed"}


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", type=Path, default=CONFIG_DIR / "default.yaml")
    parser.add_argument("--conditions", type=Path, default=CONFIG_DIR / "conditions.yaml")
    parser.add_argument("--seeds", type=int, help="number of seeds (0..N-1); defaults to the config's seed list")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    return parser


def resolve(args: argparse.Namespace) -> tuple[SimConfig, list[int]]:
    cfg = load_config(args.config)
    seeds = list(range(args.seeds)) if args.seeds else list(cfg.seeds)
    args.out.mkdir(parents=True, exist_ok=True)
    return cfg, seeds


def collect(
    cfg: SimConfig, conditions: dict[str, tuple[str, str]], seeds: Iterable[int], shock: bool
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run every (condition, seed) pair; returns per-run metrics and per-round incidence curves."""
    runs, curves = [], []
    for name, (spreader, moderator) in conditions.items():
        for seed in seeds:
            result = run_simulation(cfg, spreader, moderator, seed, shock)
            key = dict(condition=name, spreader=spreader, moderator=moderator, seed=seed, shock=shock)
            runs.append({**key, **result.metrics.as_dict()})
            curves.extend(
                {**key, "round": s.round, "new_false_exposures": s.new_false_exposures} for s in result.stats
            )
    return pd.DataFrame(runs), pd.DataFrame(curves)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "sans-serif",
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK_2,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": BASELINE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "legend.frameon": False,
            "lines.solid_capstyle": "round",
        }
    )


def title(ax, text: str, subtitle: str | None = None) -> None:
    ax.set_title(text, loc="left", fontsize=12, fontweight="bold", color=INK, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=9, color=INK_2)


def save(fig, path: Path) -> None:
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")
