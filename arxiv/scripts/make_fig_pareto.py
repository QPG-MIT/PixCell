"""fig_pareto: what a unit of capability costs, and the two ways to buy it.

Capability can be bought two different ways, and the exchange rates are not
the same:

  * across models, by moving to a stronger base model, and
  * within one model, by raising reasoning effort.

Both are drawn on one pair of axes. Every configuration sits at its measured
cost per target and its visual score; configurations of one base model are
joined in effort order, so a family reads as a short trajectory — steep where
effort buys capability cheaply, flat where it does not. The staircase marks
the Pareto set: the configurations no other beats on both cost and score.

The earlier version of this figure placed the same quantities in a 3D volume.
Flattening it costs one measured axis (compute, which tracks cost closely
enough to be redundant here) and buys back the thing a projected scatter
cannot give: a reader can put a ruler on a point.

The chatbot-era models are drawn as the low-left cloud they were. Their costs
are order-of-magnitude estimates — pipeline call count times public rates —
and are labelled as such; the agent costs are computed from measured tokens
against published list prices.

Run: .venv/bin/python arxiv/scripts/make_fig_pareto.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[2]
FIG = REPO / "arxiv" / "figures"
TABLE = Path(__file__).resolve().with_name("agent_table.json")

INK = "#17191c"
SOFT_INK = "#555a60"
GRID = "#e6e8ea"
C_ANTH = "#a31f34"
C_OAI = "#315e9f"
C_CHATBOT = "#9aa0a6"
C_FRONTIER = "#327162"
VENDOR_COLOR = {"anthropic": C_ANTH, "openai": C_OAI}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Iowan Old Style", "STIX Two Text", "STIXGeneral", "Times New Roman"],
    "mathtext.fontset": "stix",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
})

EFFORT_RANK = {"med": 0, "high": 1, "xhigh": 2, "max": 3, "ultra": 4}

# Order-of-magnitude per-target cost for the chatbot era: roughly forty
# pipeline calls at public per-token rates. Retained from the committed
# predecessor so the historical comparison does not move under our feet.
CHATBOT_COST = {
    "Gemini-2.0-Flash": 0.034, "Qwen-VL-Instruct": 0.14, "Gemini-2.5-Flash": 0.18,
    "Gemini-3-Flash": 0.23, "Gemini-2.5-Pro": 0.70, "Gemini-3-Pro": 0.92,
    "Grok-4": 1.20, "Claude-Sonnet-4.5": 1.30, "Claude-Opus-4.5": 6.0,
}


def _family(label: str) -> str:
    return label.split(" (")[0]


def _effort(label: str) -> str:
    return label.split(" (")[1].rstrip(")") if " (" in label else ""


def _pareto(points: list[dict]) -> list[dict]:
    frontier = []
    for candidate in points:
        if any(
            other is not candidate
            and other["cost"] <= candidate["cost"]
            and other["score"] >= candidate["score"]
            and (other["cost"] < candidate["cost"] or other["score"] > candidate["score"])
            for other in points
        ):
            continue
        frontier.append(candidate)
    return sorted(frontier, key=lambda p: p["cost"])


def main() -> None:
    rows = json.loads(TABLE.read_text())
    points = [
        {
            "label": row["label"], "family": _family(row["label"]),
            "effort": _effort(row["label"]), "vendor": row["vendor"],
            "generation": row.get("generation", "original"),
            "score": row["usable_iou"], "cost": row.get("median_api_equiv_cost_usd"),
        }
        for row in rows
    ]
    priced = [p for p in points if p["cost"]]
    unpriced = [p for p in points if not p["cost"]]

    chatbots = json.loads(
        (REPO / "data/chatbots/aggregates/real_success_data.json").read_text()
    )

    figure = plt.figure(figsize=(7.2, 4.4), facecolor="white")
    axes = figure.add_axes((0.085, 0.125, 0.885, 0.775))

    axes.set_xscale("log")
    axes.set_xlim(0.02, 200)
    axes.set_ylim(0, 1.08)
    axes.grid(color=GRID, linewidth=0.5, zorder=0)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        axes.spines[side].set_color(SOFT_INK)
        axes.spines[side].set_linewidth(0.6)
    axes.tick_params(length=3, width=0.6, color=SOFT_INK, labelcolor=SOFT_INK,
                     labelsize=7.0)

    # --- the chatbot era: the cloud the agent protocol moved away from
    chatbot_points = [
        (CHATBOT_COST[m["model"]], m["expected_usable_iou"])
        for m in chatbots if m["model"] in CHATBOT_COST
    ]
    axes.scatter(
        [c for c, _ in chatbot_points], [s for _, s in chatbot_points],
        s=22, facecolor="none", edgecolor=C_CHATBOT, linewidth=0.8, zorder=2,
    )
    if chatbot_points:
        ceiling = max(s for _, s in chatbot_points)
        axes.axhline(ceiling, color=C_CHATBOT, linewidth=0.6, linestyle=(0, (4, 3)),
                     zorder=1)
        axes.text(
            0.023, ceiling + 0.016, "best chatbot-era result",
            fontsize=6.0, color=C_CHATBOT, ha="left", va="bottom",
        )

    # --- effort trajectories, one polyline per base model
    by_family: dict[str, list[dict]] = {}
    for point in priced:
        by_family.setdefault(point["family"], []).append(point)
    for members in by_family.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda p: EFFORT_RANK.get(p["effort"], 0))
        axes.plot(
            [m["cost"] for m in members], [m["score"] for m in members],
            color=VENDOR_COLOR[members[0]["vendor"]], linewidth=0.85, alpha=0.45,
            zorder=3, solid_capstyle="round",
        )

    # --- the Pareto staircase
    frontier = _pareto(priced)
    staircase_x, staircase_y = [axes.get_xlim()[0]], [frontier[0]["score"]]
    for point in frontier:
        staircase_x += [point["cost"], point["cost"]]
        staircase_y += [staircase_y[-1], point["score"]]
    staircase_x.append(axes.get_xlim()[1])
    staircase_y.append(staircase_y[-1])
    axes.plot(staircase_x, staircase_y, color=C_FRONTIER, linewidth=0.9, zorder=4)

    # --- the configurations
    for point in priced:
        filled = point["generation"] == "extension"
        color = VENDOR_COLOR[point["vendor"]]
        axes.scatter(
            [point["cost"]], [point["score"]], s=26,
            facecolor=color if filled else "white",
            edgecolor=color, linewidth=0.85, zorder=5,
        )

    # A model with no published per-token price has no place on a cost axis.
    # It is named in the margin rather than given an invented coordinate.
    if unpriced:
        axes.text(
            0.985, 0.035,
            "no published rate: " + ", ".join(p["label"] for p in unpriced),
            transform=axes.transAxes, ha="right", va="bottom",
            fontsize=5.9, style="italic", color=SOFT_INK,
        )

    # --- annotate only what a reader should carry away. The frontier holds
    # eight configurations inside a 0.07 band of score; labelling all of them
    # produces a stack of overlapping text and communicates less than three
    # well-placed labels plus the line itself.
    cheapest = frontier[0]
    best = frontier[-1]
    # The knee: the largest score gain per decade of cost before the frontier
    # flattens — the configuration a practitioner would actually pick.
    knee = max(
        frontier[1:-1],
        key=lambda p: (p["score"] - cheapest["score"]) / max(p["cost"] / cheapest["cost"], 1.0),
        default=None,
    )
    callouts = [
        (cheapest, (-8, -20), "right"),
        (best, (-8, 8), "right"),
    ]
    if knee is not None and knee not in (cheapest, best):
        callouts.append((knee, (8, -14), "left"))
    for point, offset, align in callouts:
        axes.annotate(
            f"{point['label']}\n${point['cost']:.2f} · U = {point['score']:.3f}",
            (point["cost"], point["score"]),
            textcoords="offset points", xytext=offset, ha=align, va="center",
            fontsize=6.1, color=INK, linespacing=1.35, zorder=7,
            arrowprops=dict(arrowstyle="-", color=SOFT_INK, linewidth=0.5,
                            shrinkA=0, shrinkB=3),
        )

    axes.set_xlabel("API-list-price-equivalent cost per target (USD, log)",
                    fontsize=7.6, color=INK, labelpad=4)
    axes.set_ylabel(r"visual score $U$", fontsize=7.6, color=INK, labelpad=4)
    axes.set_xticks([0.03, 0.1, 0.3, 1, 3, 10, 30, 100])
    axes.set_xticklabels(["$0.03", "$0.10", "$0.30", "$1", "$3", "$10", "$30", "$100"])
    axes.minorticks_off()
    axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])

    handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=4.4,
               markerfacecolor=C_OAI, markeredgecolor=C_OAI, label="OpenAI"),
        Line2D([], [], marker="o", linestyle="none", markersize=4.4,
               markerfacecolor=C_ANTH, markeredgecolor=C_ANTH, label="Anthropic"),
        Line2D([], [], marker="o", linestyle="none", markersize=4.4,
               markerfacecolor="white", markeredgecolor=SOFT_INK, markeredgewidth=0.85,
               label="first sweep"),
        Line2D([], [], color=SOFT_INK, linewidth=0.85, alpha=0.5,
               label="effort trajectory"),
        Line2D([], [], color=C_FRONTIER, linewidth=0.9, label="Pareto frontier"),
        Line2D([], [], marker="o", linestyle="none", markersize=4.4,
               markerfacecolor="none", markeredgecolor=C_CHATBOT, label="chatbot era"),
    ]
    axes.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 0.075),
                frameon=False, fontsize=6.2, ncol=2, handletextpad=0.4,
                columnspacing=1.0, labelspacing=0.35)

    FIG.mkdir(parents=True, exist_ok=True)
    output = FIG / "fig_pareto.pdf"
    figure.savefig(output, dpi=600, facecolor="white", bbox_inches="tight")
    figure.savefig(FIG / "fig_pareto.png", dpi=300, facecolor="white", bbox_inches="tight")
    print(f"wrote {output}")
    print("Pareto set: " + " | ".join(
        f"{p['label']} ${p['cost']:.2f} U={p['score']:.3f}" for p in frontier))
    plt.close(figure)


if __name__ == "__main__":
    main()
