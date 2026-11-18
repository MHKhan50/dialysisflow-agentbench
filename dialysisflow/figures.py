"""Charts in the project colours: blue, yellow, red and green."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

BLUE, YELLOW, RED, GREEN = "#1F4E9C", "#E3A800", "#C8102E", "#5FA65A"
SHOWN = [("most_constrained_greedy", "Central greedy", GREEN), ("independent_units_gated", "Independent units + gate", RED),
         ("coordinated_units", "Coordinated units", YELLOW), ("optimal_fair", "Exact optimum (fair)", BLUE)]
LEVELS = ["low", "medium", "high"]


def make_figures(summary: Dict, out: Path) -> None:
    groups = summary["by_group"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    width = 0.2
    for k, (policy, label, colour) in enumerate(SHOWN):
        for ax, metric in zip(axes, ("fulfilment", "cohort_gap")):
            vals = [100 * groups["scarcity=%s" % s][policy][metric][0] for s in LEVELS]
            lo = [100 * groups["scarcity=%s" % s][policy][metric][1] for s in LEVELS]
            hi = [100 * groups["scarcity=%s" % s][policy][metric][2] for s in LEVELS]
            xs = [i + (k - 1.5) * width for i in range(len(LEVELS))]
            ax.bar(xs, vals, width * 0.92, color=colour, label=label,
                   yerr=[[v - a for v, a in zip(vals, lo)], [b - v for v, b in zip(vals, hi)]], capsize=2, error_kw={"lw": 0.8})
    axes[0].set_ylabel("Displaced patients placed (%)")
    axes[1].set_ylabel("Cohort unmet-rate gap (points)")
    for ax in axes:
        ax.set_xticks(range(len(LEVELS)))
        ax.set_xticklabels(["Low", "Medium", "High"])
        ax.set_xlabel("Chair scarcity at receiving units")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E6E6E6", lw=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylim(0, 105)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=4, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out / "fig_fulfilment_gap.png", dpi=200)
    fig.savefig(out / "fig_fulfilment_gap.pdf")
    plt.close(fig)
