"""Sweeps the moderator's lambda and records the exposure vs. false-positive frontier."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from common import (
    AQUA,
    INK,
    INK_2,
    SURFACE,
    apply_style,
    base_parser,
    collect,
    resolve,
    save,
    title,
)
from infodemic.config import load_conditions, override

DEFAULT_LAMBDAS = "0,0.5,1,2,5,10,20,50,200"


def sweep(cfg, conditions, seeds, lambdas) -> pd.DataFrame:
    frames = []
    for lam in lambdas:
        runs, _ = collect(override(cfg, {"moderator.lam": lam}), conditions, seeds, shock=False)
        frames.append(runs.assign(lam=lam))
    return pd.concat(frames, ignore_index=True)


def plot_frontier(frontier: pd.DataFrame, condition: str, path) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.grid(axis="x", visible=False)
    ax.plot(frontier.false_positives, frontier.total_exposure, color=AQUA, linewidth=2, zorder=2)
    ax.scatter(
        frontier.false_positives, frontier.total_exposure, s=64, color=AQUA, edgecolor=SURFACE, linewidth=2, zorder=3
    )
    for i, row in enumerate(frontier.itertuples()):
        steep = row.false_positives < 1.0
        offset, align = ((10, -3), "left") if steep else ((0, 10 if i % 2 == 0 else -14), "center")
        ax.annotate(
            f"λ={row.lam:g}",
            (row.false_positives, row.total_exposure),
            xytext=offset,
            textcoords="offset points",
            ha=align,
            fontsize=9,
            color=INK_2,
        )
    ax.set_xlabel("False positives per run (true claims suppressed)")
    ax.set_ylabel("Total exposure")
    ax.margins(x=0.08, y=0.12)
    title(
        ax,
        f"Exposure vs. false-positive frontier ({condition})",
        "Each point is the mean over seeds at one λ; lower is better on both axes",
    )
    ax.text(0.98, 0.95, "low λ: aggressive", transform=ax.transAxes, ha="right", fontsize=9, color=INK)
    ax.text(0.02, 0.05, "high λ: cautious", transform=ax.transAxes, ha="left", fontsize=9, color=INK)
    save(fig, path)


def main() -> None:
    parser = base_parser(__doc__)
    parser.add_argument("--condition", default="C6", help="condition from the conditions file to sweep")
    parser.add_argument("--lams", default=DEFAULT_LAMBDAS, help="comma-separated lambda values")
    args = parser.parse_args()
    cfg, seeds = resolve(args)
    conditions = load_conditions(args.conditions)
    if args.condition not in conditions:
        raise SystemExit(f"unknown condition {args.condition!r}; choose from {sorted(conditions)}")
    lambdas = [float(x) for x in args.lams.split(",")]

    runs = sweep(cfg, {args.condition: conditions[args.condition]}, seeds, lambdas)
    runs.to_csv(args.out / "lambda_sweep_runs.csv", index=False)

    columns = ["total_exposure", "false_positives", "takedowns", "false_positive_rate", "time_to_containment"]
    frontier = runs.groupby("lam")[columns].mean().reset_index().round(3)
    frontier["objective_at_lam"] = (frontier.total_exposure + frontier.lam * frontier.false_positives).round(1)
    frontier.to_csv(args.out / "lambda_sweep.csv", index=False)
    print(frontier.to_string(index=False))
    plot_frontier(frontier, args.condition, args.out / "lambda_frontier.png")


if __name__ == "__main__":
    main()
