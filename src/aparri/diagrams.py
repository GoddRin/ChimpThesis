"""Schematic (not data) figures for the method documentation."""
from __future__ import annotations

from pathlib import Path


def transect_diagram(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    fig, ax = plt.subplots(figsize=(11, 5.2))
    x = np.linspace(0, 10, 200)
    land_edge = 0.25 * np.sin(x * 0.9) + 2.2
    s90 = 3.4 + 0.25 * np.sin(x * 0.9 + 0.2)
    s25 = 2.95 + 0.25 * np.sin(x * 0.9 + 0.2) + 0.1 * np.sin(x * 2.3)
    ax.fill_between(x, 0, 1.2, color="#e8dcb5", label="land")
    ax.fill_between(x, 3.2, 5.2, color="#cfe6f5", alpha=0.0)
    ax.plot(x, np.full_like(x, 1.2), color="k", lw=2.2, ls="--", label="BASELINE (on land, behind every shoreline)")
    ax.plot(x, s90, color="#1f3a93", lw=2.2, label="shoreline 1990")
    ax.plot(x, s25, color="#f39c12", lw=2.2, label="shoreline 2025")
    for xt in np.arange(1, 10, 1.5):
        ax.plot([xt, xt], [0.55, 4.7], color="0.35", lw=0.9)
        y1 = 3.4 + 0.25 * np.sin(xt * 0.9 + 0.2); y2 = 2.95 + 0.25 * np.sin(xt * 0.9 + 0.2) + 0.1 * np.sin(xt * 2.3)
        ax.plot([xt], [y1], "o", color="#1f3a93"); ax.plot([xt], [y2], "o", color="#f39c12")
    xt = 4.0
    y1 = 3.4 + 0.25 * np.sin(xt * 0.9 + 0.2); y2 = 2.95 + 0.25 * np.sin(xt * 0.9 + 0.2) + 0.1 * np.sin(xt * 2.3)
    ax.annotate("", xy=(xt + 0.12, y1), xytext=(xt + 0.12, 1.2), arrowprops=dict(arrowstyle="<->", color="#1f3a93"))
    ax.text(xt + 0.2, (y1 + 1.2) / 2, "d₁₉₉₀", color="#1f3a93", fontsize=12)
    ax.annotate("", xy=(xt - 0.12, y2), xytext=(xt - 0.12, 1.2), arrowprops=dict(arrowstyle="<->", color="#f39c12"))
    ax.text(xt - 0.75, (y2 + 1.2) / 2, "d₂₀₂₅", color="#f39c12", fontsize=12)
    ax.text(xt + 0.2, y1 + 0.55, "NSM = d₂₀₂₅ − d₁₉₉₀  (negative here = landward = EROSION)\nEPR = NSM ÷ 35 years", fontsize=10, bbox=dict(fc="w", ec="0.6"))
    ax.text(0.2, 0.3, "LAND", fontsize=11); ax.text(0.2, 4.6, "SEA  →  positive distances are seaward", fontsize=11)
    ax.text(5.0, 0.2, "transects: perpendicular to the baseline, every 50 m, each with its own ID", fontsize=9, color="0.25")
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.2); ax.axis("off"); ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=4, fontsize=9, frameon=False)
    ax.set_title("How the shoreline-change rate is measured (schematic)", fontsize=13)
    fig.tight_layout(); fig.savefig(out, dpi=170); plt.close(fig)


if __name__ == "__main__":
    transect_diagram(Path("outputs/maps/method_transect_diagram.png"))
