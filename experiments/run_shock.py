"""Applies the bot-swarm shock in each condition and measures recovery."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    GRID,
    INK_2,
    MODERATOR_COLORS,
    MODERATOR_LABELS,
    SPREADER_LABELS,
    apply_style,
    base_parser,
    collect,
    resolve,
    save,
)
from infodemic.config import load_conditions
from infodemic.metrics import paired_difference

SUMMARY_COLUMNS = ["recovery_time", "recovered", "total_exposure", "peak_infection", "false_positives"]


def recovery(runs: pd.DataFrame, spreader: str, moderator: str) -> np.ndarray:
    rows = runs[(runs.spreader == spreader) & (runs.moderator == moderator)].sort_values("seed")
    return rows.recovery_time.to_numpy()


def test_h3(runs: pd.DataFrame, static: list[str]) -> pd.DataFrame:
    """Recovery-time gap between each static policy and the adaptive impact-weighted moderator."""
    rng = np.random.default_rng(0)
    rows = []
    for spreader in ("random", "centrality"):
        for baseline in static:
            diff = paired_difference(recovery(runs, spreader, baseline), recovery(runs, spreader, "impact_weighted"), rng)
            rows.append((f"{baseline} - impact_weighted | {spreader} spreader", *diff))
    table = pd.DataFrame(rows, columns=["comparison", "mean_diff_rounds", "ci_low", "ci_high"])
    table["supported"] = table.ci_low > 0
    return table


def plot_curves(curves: pd.DataFrame, shock_round: int, duration: int, path) -> None:
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
    order = [m for m in MODERATOR_LABELS if m in set(curves.moderator)]
    for ax, spreader in zip(axes, ("random", "centrality")):
        mean = curves[curves.spreader == spreader].groupby(["moderator", "round"]).new_false_exposures.mean().unstack(0)
        ax.axvspan(shock_round, shock_round + duration, color=GRID, zorder=0)
        for moderator in order:
            ax.plot(
                mean.index,
                mean[moderator],
                color=MODERATOR_COLORS[moderator],
                linewidth=2,
                linestyle="--" if moderator == "impact_static" else "-",
                label=MODERATOR_LABELS[moderator],
            )
        ax.set_title(SPREADER_LABELS[spreader], loc="left", fontsize=10, color=INK_2)
        ax.set_xlabel("Round")
        ax.margins(x=0.01)
    axes[0].set_ylabel("New false exposures per round (mean)")
    axes[0].legend(loc="upper left", fontsize=9)
    fig.suptitle("Bot-swarm shock: incidence of false exposures", x=0.075, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.075, 0.905, "Shaded band marks the swarm's active rounds", fontsize=9, color=INK_2)
    fig.subplots_adjust(top=0.82)
    save(fig, path)


def main() -> None:
    parser = base_parser(__doc__)
    parser.add_argument("--k", type=int, default=15, help="rounds allowed for recovery in the H3 check")
    parser.add_argument("--with-static", action="store_true", help="add a static impact-ranking ablation")
    args = parser.parse_args()
    cfg, seeds = resolve(args)
    conditions = load_conditions(args.conditions)
    if args.with_static:
        conditions = {**conditions, "C3s": ("random", "impact_static"), "C6s": ("centrality", "impact_static")}

    runs, curves = collect(cfg, conditions, seeds, shock=True)
    runs["recovered_within_k"] = runs.recovery_time <= args.k
    runs.to_csv(args.out / "shock_runs.csv", index=False)

    summary = runs.groupby(["condition", "spreader", "moderator"])[SUMMARY_COLUMNS + ["recovered_within_k"]].mean().round(3)
    summary.to_csv(args.out / "shock_summary.csv")
    print(f"recovery = rounds after the shock until incidence stays <= {cfg.containment_threshold}/round; k = {args.k}\n")
    print(summary.to_string(), "\n")

    static = ["fifo", "random"] + (["impact_static"] if args.with_static else [])
    h3 = test_h3(runs, static)
    h3.round(2).to_csv(args.out / "shock_hypotheses.csv", index=False)
    print(h3.round(2).to_string(index=False))
    plot_curves(curves, cfg.shock.round, cfg.shock.duration, args.out / "shock_recovery.png")


if __name__ == "__main__":
    main()
