"""Checks how robust the H2 result is to the settings chosen for the default config."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    INK_2,
    MODERATOR_COLORS,
    MODERATOR_LABELS,
    SPREADER_LABELS,
    SURFACE,
    apply_style,
    base_parser,
    collect,
    resolve,
    save,
)
from infodemic.config import load_conditions, override
from infodemic.metrics import paired_difference

SWEEPS = {
    "moderator.budget_per_round": ([1, 2, 3, 5, 8], "Verification budget B per round"),
    "moderator.kb_coverage": ([0.3, 0.5, 0.7, 0.9], "Knowledge-base coverage"),
    "spreader.max_sockpuppets": ([0, 2, 5, 10, 20], "Max sockpuppets (0 = spreader does not adapt)"),
}
MODERATORS = ("random", "fifo", "impact_weighted")


def coerce(cfg, path: str, raw: str):
    current = cfg
    for part in path.split("."):
        current = getattr(current, part)
    return type(current)(float(raw))


def sweep(cfg, conditions, seeds, path: str, values) -> pd.DataFrame:
    frames = []
    for value in values:
        runs, _ = collect(override(cfg, {path: value}), conditions, seeds, shock=False)
        frames.append(runs.assign(value=value))
    return pd.concat(frames, ignore_index=True)


def h2_table(runs: pd.DataFrame) -> pd.DataFrame:
    """Does impact-weighted moderation beat FIFO and random at each setting? Paired by seed."""
    rng = np.random.default_rng(0)
    rows = []
    for (value, spreader), group in runs.groupby(["value", "spreader"]):
        exposure = {m: g.sort_values("seed").total_exposure.to_numpy() for m, g in group.groupby("moderator")}
        fifo = paired_difference(exposure["fifo"], exposure["impact_weighted"], rng)
        rand = paired_difference(exposure["random"], exposure["impact_weighted"], rng)
        rows.append(
            dict(
                value=value,
                spreader=spreader,
                fifo_minus_impact=fifo[0],
                fifo_ci_low=fifo[1],
                random_minus_impact=rand[0],
                random_ci_low=rand[1],
                h2_supported=bool(fifo[1] > 0 and rand[1] > 0),
            )
        )
    return pd.DataFrame(rows)


def plot(runs: pd.DataFrame, label: str, path) -> None:
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
    values = sorted(runs.value.unique())
    xs = list(range(len(values)))
    for ax, spreader in zip(axes, ("random", "centrality")):
        data = runs[runs.spreader == spreader]
        for moderator in MODERATORS:
            g = data[data.moderator == moderator].groupby("value").total_exposure
            ax.errorbar(
                xs,
                g.mean().reindex(values),
                yerr=(1.96 * g.std() / np.sqrt(g.count())).reindex(values),
                color=MODERATOR_COLORS[moderator],
                linewidth=2,
                marker="o",
                markersize=8,
                markeredgecolor=SURFACE,
                markeredgewidth=2,
                elinewidth=1,
                capsize=3,
                label=MODERATOR_LABELS[moderator],
            )
        ax.set_xticks(xs, [f"{v:g}" for v in values])
        ax.set_xlabel(label)
        ax.grid(axis="x", visible=False)
        ax.set_title(SPREADER_LABELS[spreader], loc="left", fontsize=10, color=INK_2)
    axes[0].set_ylabel("Total exposure (mean)")
    axes[0].legend(loc="upper right", fontsize=9)
    fig.suptitle(f"Sensitivity of total exposure: {label}", x=0.075, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.075, 0.905, "Mean over seeds; whiskers are 95% confidence intervals", fontsize=9, color=INK_2)
    fig.subplots_adjust(top=0.82)
    save(fig, path)


def main() -> None:
    parser = base_parser(__doc__)
    parser.add_argument("--param", choices=sorted(SWEEPS), help="sweep one parameter (default: all)")
    parser.add_argument("--values", help="comma-separated values for --param")
    args = parser.parse_args()
    cfg, seeds = resolve(args)
    conditions = load_conditions(args.conditions)

    tables = []
    for path in [args.param] if args.param else list(SWEEPS):
        defaults, label = SWEEPS[path]
        values = [coerce(cfg, path, v) for v in args.values.split(",")] if args.values else defaults
        runs = sweep(cfg, conditions, seeds, path, values)
        name = path.split(".")[-1]
        runs.to_csv(args.out / f"sensitivity_{name}_runs.csv", index=False)
        plot(runs, label, args.out / f"sensitivity_{name}.png")
        tables.append(h2_table(runs).assign(param=path))

    h2 = pd.concat(tables, ignore_index=True)
    h2.round(2).to_csv(args.out / "sensitivity_h2.csv", index=False)
    print(h2.round(1).to_string(index=False))
    print(f"\nH2 supported in {int(h2.h2_supported.sum())} of {len(h2)} settings")


if __name__ == "__main__":
    main()
