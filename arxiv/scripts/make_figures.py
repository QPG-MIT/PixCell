"""Figures for the agents-not-chatbots emergence paper.

Data sources:
- June 2026 API-harness leaderboard: main worktree data/chatbots/aggregates/real_success_data.json
  (metric: expected_usable_iou = primitive_rate x avg IoU of primitive runs)
- July 2026 agent sweep: data/agents/paper_swap/sweep_results.json (this worktree)
- Per-cell run metrics: data/agents/paper_swap/sweep_metrics.json

Output: PDFs -> arxiv/figures/ (what the paper
includes); PNG previews -> arxiv/figures/.

Run: .venv/bin/python arxiv/scripts/make_figures.py
"""
import json
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
FIG = REPO / "arxiv/figures"
ARXIV = REPO / "arxiv/figures"
FIG.mkdir(parents=True, exist_ok=True)

JUNE = json.loads((REPO / "data/chatbots/aggregates/real_success_data.json").read_text())
SWEEP = json.loads((REPO / "data/agents/paper_swap/sweep_results.json").read_text())["cells"]
try:
    METRICS = json.loads((REPO / "data/agents/paper_swap/sweep_metrics.json").read_text())["cells"]
except FileNotFoundError:
    METRICS = []

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "pdf.fonttype": 42, "font.size": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "savefig.bbox": "tight", "figure.dpi": 200,
})


def save(fig, stem):
    fig.savefig(ARXIV / f"{stem}.pdf")
    fig.savefig(FIG / f"{stem}.png")
    plt.close(fig)
    print(f"wrote {ARXIV / (stem + '.pdf')}")

AGENT_LABEL = {
    # --- original generation ---
    "haiku45m": "Haiku 4.5 (med)", "haiku45h": "Haiku 4.5 (high)",
    "sonnet45m": "Sonnet 4.5", "sonnet5m": "Sonnet 5",
    "opus45m": "Opus 4.5", "opus48m": "Opus 4.8 (med)", "opus48max": "Opus 4.8 (max)",
    "codexspark": "GPT-5.3 spark", "codex54mini": "GPT-5.4-mini", "codex54m": "GPT-5.4",
    "codex55m": "GPT-5.5 (med)", "codex55h": "GPT-5.5 (high)", "codex55x": "GPT-5.5 (xhigh)",
    # --- extension: the newer generation, same protocol ---
    "opus5m": "Opus 5 (med)", "opus5max": "Opus 5 (max)",
    "fable5m": "Fable 5 (med)", "fable5max": "Fable 5 (max)",
    "codex56lunam": "GPT-5.6 luna (med)", "codex56lunax": "GPT-5.6 luna (xhigh)",
    "codex56lunau": "GPT-5.6 luna (ultra)",
    "codex56terram": "GPT-5.6 terra (med)", "codex56terrax": "GPT-5.6 terra (xhigh)",
    "codex56terrau": "GPT-5.6 terra (ultra)",
    "codex56solm": "GPT-5.6 sol (med)", "codex56solx": "GPT-5.6 sol (xhigh)",
    "codex56solu": "GPT-5.6 sol (ultra)",
}
# Vendor is read from the rate card rather than inferred from a name prefix:
# the prefix rule silently mislabels any configuration whose name does not
# begin with a known family (it had no branch for "fable" at all).
_RATE_CARD = json.loads(
    (REPO / "data/agents/paper_swap/rate_card.json").read_text()
)
VENDOR = {
    cfg: _RATE_CARD["models"][_RATE_CARD["config_to_model"][cfg]]["vendor"]
    for cfg in AGENT_LABEL
}
EXTENSION = {
    "opus5m", "opus5max", "fable5m", "fable5max",
    "codex56lunam", "codex56lunax", "codex56lunau",
    "codex56terram", "codex56terrax", "codex56terrau",
    "codex56solm", "codex56solx", "codex56solu",
}
C_ANTH, C_OAI, C_JUNE, INK = "#c15f3c", "#3c7ec1", "#8a8a8a", "#16161d"


def config_cells(cfg):
    return [c for c in SWEEP if c["config"] == cfg]


def usable_iou(cfg):
    """Same formula as the June metric: pure_rate x mean IoU of pure runs."""
    cells = config_cells(cfg)
    if not cells:
        return None
    pure = [c["iou"] for c in cells if not c["purity_violation"] and c["iou"] is not None]
    if not pure:
        return 0.0
    return (len(pure) / len(cells)) * mean(pure)


def mean_iou(cfg):
    vals = [c["iou"] for c in config_cells(cfg) if c["iou"] is not None]
    return mean(vals) if vals else None


# ---------------------------------------------------------------- fig 1: the jump
def fig1():
    june = sorted(JUNE, key=lambda m: m["expected_usable_iou"])
    agents = [c for c in AGENT_LABEL if config_cells(c)]
    agents.sort(key=lambda c: usable_iou(c))

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    jx = list(range(len(june)))
    ax.scatter(jx, [m["expected_usable_iou"] for m in june], s=42, color=C_JUNE,
               zorder=3, label="API/chatbot harness (June 2026)")
    gap = 2.6
    ax_x = [len(june) - 1 + gap + i * 1.25 for i in range(len(agents))]
    for x, cfg in zip(ax_x, agents):
        color = C_ANTH if VENDOR[cfg] == "anthropic" else C_OAI
        ax.scatter([x], [usable_iou(cfg)], s=48, color=color, zorder=3)

    # same-weights connectors
    june_by_name = {m["model"]: m["expected_usable_iou"] for m in JUNE}
    pairs = [("claude-opus-4.5", "opus45m"), ("claude-sonnet-4.5", "sonnet45m")]
    for jn, cfg in pairs:
        jv = next((v for k, v in june_by_name.items() if jn.replace("claude-", "") in k.lower()), None)
        if jv is None or cfg not in agents:
            continue
        x0 = jx[[m["expected_usable_iou"] for m in june].index(jv)]
        x1 = ax_x[agents.index(cfg)]
        ax.annotate("", xy=(x1, usable_iou(cfg)), xytext=(x0, jv),
                    arrowprops=dict(arrowstyle="->", color=C_ANTH, lw=1.0, alpha=0.65,
                                    connectionstyle="arc3,rad=-0.25"))
        ax.text((x0 + x1) / 2, (jv + usable_iou(cfg)) / 2 + 0.04, "same weights",
                fontsize=7, color=C_ANTH, ha="center", style="italic")

    def short_june(name):
        n = name.lower()
        for pat, rep in (("gemini-", "g"), ("claude-", ""), ("qwen3-vl-235b-a22b-instruct", "qwen-vl"),
                         ("qwen-vl-instruct", "qwen-vl"), ("-preview", ""), ("-flash", "F"), ("-pro", "P")):
            n = n.replace(pat, rep)
        return n
    SHORT_AGENT = {
        "haiku45m": "haiku4.5", "haiku45h": "haiku4.5 hi", "sonnet45m": "sonnet4.5",
        "sonnet5m": "sonnet5", "opus45m": "opus4.5", "opus48m": "opus4.8",
        "opus48max": "opus4.8 max", "codexspark": "5.3-spark", "codex54mini": "5.4-mini",
        "codex54m": "5.4", "codex55m": "5.5 med", "codex55h": "5.5 hi", "codex55x": "5.5 xhi",
    }
    for x, m in zip(jx, june):
        y = m["expected_usable_iou"]
        ax.text(x - 0.1, y + 0.035, short_june(m["model"]),
                rotation=42, ha="left", va="bottom", fontsize=6, color="#555")
    for x, cfg in zip(ax_x, agents):
        y = usable_iou(cfg)
        ax.text(x - 0.1, y + 0.035, SHORT_AGENT[cfg], rotation=42,
                ha="left", va="bottom", fontsize=6, color="#333")

    ax.axvspan(-0.7, len(june) - 0.4, color="#000", alpha=0.04)
    ax.text((len(june) - 1) / 2, 1.10, "models as chatbots", ha="center", fontsize=9,
            color="#666", clip_on=False)
    ax.text(mean(ax_x), 1.10, "the same class of models, as agents", ha="center",
            fontsize=9, clip_on=False)
    ax.scatter([], [], s=48, color=C_ANTH, label="agent harness — Anthropic")
    ax.scatter([], [], s=48, color=C_OAI, label="agent harness — OpenAI")
    ax.set_ylabel("expected usable IoU\n(primitive-discipline rate × IoU)")
    ax.set_xticks([])
    ax.set_ylim(-0.02, 1.04)
    ax.legend(loc="upper left", fontsize=7, frameon=False, bbox_to_anchor=(0.0, 1.0))
    fig.savefig(FIG / "fig1_emergence.pdf")
    fig.savefig(FIG / "fig1_emergence.png")
    plt.close(fig)


# --------------------------------------------------- fig 2: agent panel zoom
def fig2():
    agents = [c for c in AGENT_LABEL if config_cells(c)]
    agents.sort(key=lambda c: mean_iou(c))
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    ax.grid(axis="x", color="#dddddd", lw=0.5, zorder=0)
    for i, cfg in enumerate(agents):
        cells = config_cells(cfg)
        color = C_ANTH if VENDOR[cfg] == "anthropic" else C_OAI
        for c in cells:
            if c["iou"] is None:
                continue
            if c["purity_violation"]:
                ax.scatter(c["iou"], i, s=16, color=color, marker="x",
                           alpha=0.85, zorder=3, linewidths=0.9)
            else:
                ax.scatter(c["iou"], i, s=11, color=color, marker="o",
                           alpha=0.7, zorder=3, linewidths=0)
        mv = mean_iou(cfg)
        ax.plot([mv, mv], [i - 0.34, i + 0.34], color=color, lw=1.4, zorder=4)
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([AGENT_LABEL[c] for c in agents], fontsize=7)
    ax.set_xlabel("IoU vs. target device\n(8 devices per config; $\\times$ = broke primitives rule)",
                  fontsize=7.5, color=INK)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(-0.6, len(agents) - 0.4)
    ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    save(fig, "fig2_agent_zoom")


# --------------------------------------------------- fig 3: heatmap config x device
def fig3():
    agents = [c for c in AGENT_LABEL if config_cells(c)]
    agents.sort(key=lambda c: mean_iou(c), reverse=True)
    devices = [f"final{i}" for i in range(1, 9)]
    def val(cfg, d):
        cell = next((c for c in config_cells(cfg) if c["device"] == d), None)
        return cell["iou"] if cell and cell["iou"] is not None else float("nan")
    grid = [[val(cfg, d) for d in devices] for cfg in agents]
    fig, ax = plt.subplots(figsize=(3.4, 3.1))
    im = ax.imshow(grid, cmap="viridis", vmin=0, vmax=1, aspect="auto",
                   interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02,
                        ticks=[0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_label("IoU", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=2)
    cbar.outline.set_visible(False)
    # thin white rules between cells
    ax.set_xticks([x - 0.5 for x in range(1, 8)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(agents))], minor=True)
    ax.grid(which="minor", color="white", lw=0.5)
    ax.tick_params(which="minor", length=0)
    ax.set_xticks(range(8))
    ax.set_xticklabels([f"F{i}" for i in range(1, 9)], fontsize=7)
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([AGENT_LABEL[c] for c in agents], fontsize=7)
    for i, cfg in enumerate(agents):
        for j, d in enumerate(devices):
            cell = next((c for c in config_cells(cfg) if c["device"] == d), None)
            if cell and cell["iou"] is not None:
                mark = "*" if cell["purity_violation"] else ""
                dark = cell["iou"] < 0.52
                ax.text(j, i, f'{cell["iou"]:.2f}{mark}', ha="center",
                        va="center", fontsize=5.6,
                        color="white" if dark else INK)
            else:
                ax.text(j, i, "–", ha="center", va="center", fontsize=6,
                        color="#888888")
    ax.set_xlabel("device (* = source-compliance violation)", fontsize=7.5,
                  color="#555555")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "fig3_heatmap")


# --------------------------------------------------- fig 4: effort + generation
def fig4():
    fig, a2 = plt.subplots(figsize=(3.4, 2.2))
    # generation ladders — per-point tier labels, vendor name at line end
    lad_a = [("Haiku 4.5", "haiku45m"), ("Sonnet 4.5", "sonnet45m"),
             ("Opus 4.5", "opus45m"), ("Sonnet 5", "sonnet5m"), ("Opus 4.8", "opus48m")]
    lad_o = [("5.3-spark", "codexspark"), ("5.4-mini", "codex54mini"),
             ("5.4", "codex54m"), ("5.5", "codex55m")]
    for lad, color, name, vend_xy, dy in ((lad_a, C_ANTH, "Anthropic", (0.18, 0.47), -8),
                                          (lad_o, C_OAI, "OpenAI", (1.45, 0.93), 5)):
        xs, ys = [], []
        for lbl, cfg in lad:
            if config_cells(cfg):
                xs.append(lbl)
                ys.append(mean_iou(cfg))
        a2.plot(range(len(xs)), ys, marker="o", color=color, ms=2.8, lw=1.1)
        a2.text(*vend_xy, name, fontsize=7, color=color, ha="left",
                va="center", style="italic")
        for i, (x, y) in enumerate(zip(xs, ys)):
            a2.annotate(x, (i, y), textcoords="offset points", xytext=(0, dy),
                        fontsize=6, ha="center", color=color,
                        va="bottom" if dy > 0 else "top")
    a2.set_ylim(0, 1)
    a2.set_ylabel("mean IoU", fontsize=7.5)
    a2.set_xticks([])
    a2.set_xlim(-0.5, 4.5)
    a2.set_xlabel("model tier / generation (ordered)", fontsize=7.5)
    a2.tick_params(axis="y", labelsize=6.5)
    a2.spines["bottom"].set_visible(False)
    fig.tight_layout()
    save(fig, "fig4_effort_generation")


# --------------------------------------------------- table: cost/compute per config
# Cost is NOT recomputed here. data/agents/paper_swap/compilation.json is the
# single source of truth: it applies each vendor's own token accounting (the
# buckets are disjoint for Anthropic and nested for OpenAI) against published
# list prices recorded with their sources in rate_card.json. The former local
# model hardcoded one Anthropic price triple, applied it by name prefix, and
# had no branch for configurations outside that convention.
COMPILATION = json.loads(
    (REPO / "data/agents/paper_swap/compilation.json").read_text()
)


def table():
    # One canonical location, beside the generator: the emergence manifest pins
    # it as ../agent_table.json and make_fig_pareto3d.py reads it by name. It
    # used to be written into figures/ instead, leaving two divergent copies.
    out = Path(__file__).resolve().with_name("agent_table.json")
    by_config = {row["config"]: row for row in COMPILATION["by_configuration"]}
    rows = []
    for cfg in AGENT_LABEL:
        cells = config_cells(cfg)
        if not cells:
            continue
        summary = by_config.get(cfg, {})
        rows.append({
            "config": cfg, "label": AGENT_LABEL[cfg], "vendor": VENDOR[cfg],
            "generation": "extension" if cfg in EXTENSION else "original",
            "mean_iou": round(mean_iou(cfg), 3), "usable_iou": round(usable_iou(cfg), 3),
            "violations": sum(1 for c in cells if c["purity_violation"]),
            "n": len(cells),
            "median_wall_min": summary.get("median_wall_min"),
            "wall_comparable": summary.get("wall_comparable"),
            "median_iterations": summary.get("median_iterations"),
            "median_output_tokens": summary.get("median_output_tokens"),
            "median_api_equiv_cost_usd": summary.get("median_cost_usd"),
            "cost_cells_priced": summary.get("cost_cells_priced"),
        })
    rows.sort(key=lambda r: r["mean_iou"], reverse=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"table -> {out}")
    for r in rows:
        cost = r["median_api_equiv_cost_usd"]
        cost_s = f"${cost:.2f}" if cost is not None else "unpriced"
        print(f'{r["label"]:<22} IoU {r["mean_iou"]:.3f} usable {r["usable_iou"]:.3f} '
              f'viol {r["violations"]} wall {r["median_wall_min"]}m '
              f'tok {r["median_output_tokens"]} cost {cost_s}')


if __name__ == "__main__":
    # The combined model-evaluation and benchmark-matrix figure is generated
    # by make_fig_emergence.py. Do not call fig1() or fig3() here: they are
    # retained only as provenance for the superseded standalone plots.
    fig2()
    fig4()
    table()
    print(f"figures -> {FIG}")
