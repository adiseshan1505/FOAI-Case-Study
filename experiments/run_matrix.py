"""Runs the 2 x 3 experiment matrix (C1-C6) over multiple seeds."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    INK,
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
    title,
)
from infodemic.config import load_conditions
from infodemic.metrics import paired_difference

SUMMARY_COLUMNS = ["total_exposure", "peak_infection", "time_to_containment", "false_positives", "false_positive_rate"]


def exposure(runs: pd.DataFrame, spreader: str, moderator: str) -> np.ndarray:
    rows = runs[(runs.spreader == spreader) & (runs.moderator == moderator)].sort_values("seed")
    return rows.total_exposure.to_numpy()


def test_hypotheses(runs: pd.DataFrame) -> pd.DataFrame:
    """Paired comparisons by seed: same graph, knowledge base and organic claims on both sides."""
    rng = np.random.default_rng(0)
    rows = []
    for m in ("random", "fifo", "impact_weighted"):
        diff = paired_difference(exposure(runs, "centrality", m), exposure(runs, "random", m), rng)
        rows.append(("H1", f"centrality - random targeting | {m} moderator", *diff))
    for s in ("random", "centrality"):
        for baseline in ("fifo", "random"):
            diff = paired_difference(exposure(runs, s, baseline), exposure(runs, s, "impact_weighted"), rng)
            rows.append(("H2", f"{baseline} - impact_weighted | {s} spreader", *diff))
    table = pd.DataFrame(rows, columns=["hypothesis", "comparison", "mean_diff", "ci_low", "ci_high"])
    table["supported"] = table.ci_low > 0
    return table


def plot_exposure(summary: pd.DataFrame, path) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    spreaders = ["random", "centrality"]
    moderators = ["random", "fifo", "impact_weighted"]
    width, gap = 0.24, 0.02
    for j, m in enumerate(moderators):
        xs, means, errs = [], [], []
        for i, s in enumerate(spreaders):
            row = summary.loc[(s, m)]
            xs.append(i + (j - 1) * (width + gap))
            means.append(row["mean"])
            errs.append(row["ci"])
        ax.bar(xs, means, width, color=MODERATOR_COLORS[m], edgecolor=SURFACE, linewidth=2, label=MODERATOR_LABELS[m])
        ax.errorbar(xs, means, yerr=errs, fmt="none", ecolor=INK_2, elinewidth=1, capsize=3)
        for x, y, e in zip(xs, means, errs):
            ax.text(x, y + e + 15, f"{y:,.0f}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(range(len(spreaders)), [SPREADER_LABELS[s] for s in spreaders])
    ax.set_ylabel("Total exposure (users exposed to false claims)")
    ax.tick_params(axis="x", length=0)
    ax.legend(title="Moderator", title_fontproperties={"size": 9}, loc="upper left")
    title(ax, "Total exposure by targeting and moderation policy", "Mean over seeds; whiskers are 95% confidence intervals")
    save(fig, path)


def main() -> None:
    args = base_parser(__doc__).parse_args()
    cfg, seeds = resolve(args)
    conditions = load_conditions(args.conditions)
    runs, _ = collect(cfg, conditions, seeds, shock=False)
    runs.to_csv(args.out / "matrix_runs.csv", index=False)

    grouped = runs.groupby(["condition", "spreader", "moderator"])[SUMMARY_COLUMNS]
    summary = grouped.mean().join(grouped.std().add_suffix("_std")).round(3)
    summary.to_csv(args.out / "matrix_summary.csv")
    print(summary[SUMMARY_COLUMNS].to_string(), "\n")

    hypotheses = test_hypotheses(runs)
    hypotheses.round(2).to_csv(args.out / "matrix_hypotheses.csv", index=False)
    print(hypotheses.round(2).to_string(index=False))

    stats = runs.groupby(["spreader", "moderator"]).total_exposure.agg(["mean", "std", "count"])
    stats["ci"] = 1.96 * stats["std"] / np.sqrt(stats["count"])
    plot_exposure(stats, args.out / "matrix_exposure.png")


if __name__ == "__main__":
    main()
