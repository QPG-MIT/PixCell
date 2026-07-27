#!/usr/bin/env python3
"""
JEE Exploration Visualization

Creates matplotlib figures for visualizing the two-phase exploration process:
- Phase 1: Grid search results
- Phase 2: Parallel Powell + Nelder-Mead optimization

Generates figures for:
- Grid search SSE distribution
- Method comparison (Powell vs Nelder-Mead)
- Convergence curves from iteration histories
- Parameter evolution during optimization
- Exploration summary
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches


# Color scheme
COLORS = {
    "powell": "#E74C3C",  # Red
    "nelder-mead": "#3498DB",  # Blue
    "best": "#2ECC71",  # Green
    "feasible": "#2ECC71",  # Green
    "infeasible": "#E74C3C",  # Red
    "baseline": "#95A5A6",  # Gray
    "grid": "#9B59B6",  # Purple
}

# Method colors for convergence
METHOD_COLORS = {
    "Powell": "#E74C3C",
    "Nelder-Mead": "#3498DB",
}

# Rank colors
RANK_COLORS = ["#2ECC71", "#F1C40F", "#E67E22"]  # Green, Yellow, Orange


def setup_dark_style():
    """Configure matplotlib for dark theme."""
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": "#0a0a0a",
            "axes.facecolor": "#1a1a1a",
            "axes.edgecolor": "white",
            "axes.labelcolor": "white",
            "text.color": "white",
            "xtick.color": "white",
            "ytick.color": "white",
            "grid.color": "#333333",
            "legend.facecolor": "#1a1a1a",
            "legend.edgecolor": "white",
        }
    )


def setup_light_style():
    """Configure matplotlib for light theme."""
    plt.style.use("seaborn-v0_8-whitegrid")


def load_exploration_results(results_dir: Path) -> Tuple[Dict, Optional[Dict]]:
    """
    Load exploration results from JSON files.

    Returns:
        (exploration_result, grid_results) - grid_results may be None
    """
    results_dir = Path(results_dir)

    exploration_file = results_dir / "exploration_result.json"
    if not exploration_file.exists():
        raise FileNotFoundError(f"exploration_result.json not found in {results_dir}")

    with open(exploration_file) as f:
        exploration = json.load(f)

    grid_results = None
    grid_file = results_dir / "grid_results.json"
    if grid_file.exists():
        with open(grid_file) as f:
            grid_results = json.load(f)

    return exploration, grid_results


def load_iteration_histories(results_dir: Path) -> Dict[str, Dict]:
    """
    Load iteration histories from optimization subdirectories.

    Returns:
        Dict mapping run_id (e.g., "powell_rank1") to history data
    """
    results_dir = Path(results_dir)
    histories = {}

    for subdir in results_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith("opt_"):
            history_file = subdir / "iteration_history.json"
            if history_file.exists():
                with open(history_file) as f:
                    data = json.load(f)
                # Extract method and rank from directory name (e.g., "opt_powell_rank1")
                parts = subdir.name.split("_")
                if len(parts) >= 3:
                    method = parts[1]
                    rank = parts[2].replace("rank", "")
                    run_id = f"{method}_rank{rank}"
                    histories[run_id] = data

    return histories


def plot_grid_search_overview(
    ax: plt.Axes, grid_results: Dict, exploration: Dict
) -> None:
    """Plot SSE distribution across grid points."""
    grid_points = grid_results.get("grid_points", [])
    if not grid_points:
        ax.text(0.5, 0.5, "No grid data", ha="center", va="center", transform=ax.transAxes)
        return

    # Extract data
    indices = list(range(len(grid_points)))
    sse_values = [gp["sse"] for gp in grid_points]
    feasible = [gp.get("within_footprint", True) for gp in grid_points]

    # Filter out inf values for plotting
    valid_mask = [s < float("inf") for s in sse_values]
    valid_indices = [i for i, v in zip(indices, valid_mask) if v]
    valid_sse = [s for s, v in zip(sse_values, valid_mask) if v]
    valid_feasible = [f for f, v in zip(feasible, valid_mask) if v]

    if not valid_sse:
        ax.text(0.5, 0.5, "No valid SSE values", ha="center", va="center", transform=ax.transAxes)
        return

    # Plot points
    feas_indices = [i for i, f in zip(valid_indices, valid_feasible) if f]
    feas_sse = [s for s, f in zip(valid_sse, valid_feasible) if f]
    infeas_indices = [i for i, f in zip(valid_indices, valid_feasible) if not f]
    infeas_sse = [s for s, f in zip(valid_sse, valid_feasible) if not f]

    if feas_indices:
        ax.scatter(
            feas_indices, feas_sse, c=COLORS["feasible"], alpha=0.6, s=20, label="Feasible"
        )
    if infeas_indices:
        ax.scatter(
            infeas_indices, infeas_sse, c=COLORS["infeasible"], alpha=0.6, s=20, marker="x", label="Infeasible"
        )

    # Highlight best grid point
    best_idx = min(range(len(valid_sse)), key=lambda i: valid_sse[i])
    ax.scatter(
        [valid_indices[best_idx]], [valid_sse[best_idx]],
        c=COLORS["best"], s=100, marker="*", zorder=10, label=f"Best: {valid_sse[best_idx]:,.0f}"
    )

    # Add baseline reference
    baseline_sse = exploration.get("baseline_sse", 0)
    if baseline_sse and baseline_sse < float("inf"):
        ax.axhline(y=baseline_sse, color=COLORS["baseline"], linestyle="--", alpha=0.7, label=f"Baseline: {baseline_sse:,.0f}")

    ax.set_xlabel("Grid Point Index")
    ax.set_ylabel("SSE")
    ax.set_title("Grid Search: SSE Distribution")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)


def plot_method_comparison(ax: plt.Axes, exploration: Dict) -> None:
    """Plot Powell vs Nelder-Mead comparison."""
    local_results = exploration.get("local_opt_results", [])
    if not local_results:
        ax.text(0.5, 0.5, "No optimization results", ha="center", va="center", transform=ax.transAxes)
        return

    # Group by starting rank
    by_rank = {}
    for r in local_results:
        rank = r.get("starting_rank", 1)
        method = r.get("method", "Unknown")
        if rank not in by_rank:
            by_rank[rank] = {}
        by_rank[rank][method] = r.get("best_sse", float("inf"))

    ranks = sorted(by_rank.keys())
    methods = ["Powell", "Nelder-Mead"]
    x = np.arange(len(ranks))
    width = 0.35

    for i, method in enumerate(methods):
        values = [by_rank[rank].get(method, 0) for rank in ranks]
        offset = (i - 0.5) * width
        color = METHOD_COLORS.get(method, "#888888")
        bars = ax.bar(x + offset, values, width, label=method, color=color, alpha=0.8)

    # Mark the overall best
    best_method = exploration.get("best_method", "")
    best_sse = exploration.get("best_sse", 0)
    best_rank = exploration.get("best_starting_rank", 1)

    ax.set_xlabel("Starting Grid Rank")
    ax.set_ylabel("Final SSE")
    ax.set_title(f"Method Comparison (Best: {best_method} from rank {best_rank})")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Rank {r}" for r in ranks])
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")


def plot_improvement_breakdown(ax: plt.Axes, exploration: Dict) -> None:
    """Plot improvement percentages by method and rank."""
    local_results = exploration.get("local_opt_results", [])
    if not local_results:
        ax.text(0.5, 0.5, "No optimization results", ha="center", va="center", transform=ax.transAxes)
        return

    # Sort by improvement
    sorted_results = sorted(local_results, key=lambda r: r.get("improvement", 0), reverse=True)

    labels = []
    improvements = []
    colors = []

    for r in sorted_results:
        method = r.get("method", "Unknown")
        rank = r.get("starting_rank", 1)
        imp = r.get("improvement", 0)
        labels.append(f"{method}\nRank {rank}")
        improvements.append(imp)
        colors.append(METHOD_COLORS.get(method, "#888888"))

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, improvements, color=colors, alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Improvement from Starting Point (%)")
    ax.set_title("Improvement by Optimization Run")
    ax.grid(True, alpha=0.3, axis="x")


def plot_convergence_curves(ax: plt.Axes, histories: Dict[str, Dict]) -> None:
    """Plot SSE convergence curves for all optimization runs."""
    if not histories:
        ax.text(0.5, 0.5, "No iteration histories found", ha="center", va="center", transform=ax.transAxes)
        return

    for run_id, data in histories.items():
        history = data.get("history", [])
        if not history:
            continue

        iterations = [h["iteration"] for h in history]
        sse_values = [h["sse"] for h in history]

        # Determine color and style
        parts = run_id.split("_")
        method = parts[0].title() if parts else "Unknown"
        rank = int(parts[1].replace("rank", "")) if len(parts) > 1 else 1

        color = METHOD_COLORS.get(method, "#888888")
        linestyle = "-" if rank == 1 else "--" if rank == 2 else ":"

        # Filter out inf values
        valid = [(i, s) for i, s in zip(iterations, sse_values) if s < float("inf")]
        if valid:
            iters, sses = zip(*valid)
            ax.plot(iters, sses, color=color, linestyle=linestyle, alpha=0.8,
                    label=f"{method} R{rank}")

    ax.set_xlabel("Iteration")
    ax.set_ylabel("SSE")
    ax.set_title("Optimization Convergence")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)


def plot_parameter_evolution(
    fig: plt.Figure, history_data: Dict, output_path: Path
) -> None:
    """Create parameter evolution figure for a single optimization run."""
    history = history_data.get("history", [])
    metadata = history_data.get("metadata", {})
    param_names = metadata.get("param_names", [])

    if not history or not param_names:
        return

    # Check if params are recorded in history
    if "params" not in history[0]:
        return

    n_params = len(param_names)
    n_cols = min(3, n_params)
    n_rows = (n_params + n_cols - 1) // n_cols

    fig_params, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows))
    if n_params == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    iterations = [h["iteration"] for h in history]
    is_best = [h.get("is_best", False) for h in history]

    for idx, param_name in enumerate(param_names):
        ax = axes[idx]
        values = [h["params"].get(param_name, 0) for h in history]

        ax.plot(iterations, values, "b-", alpha=0.6, linewidth=1)

        # Highlight best iterations
        best_iters = [i for i, b in zip(iterations, is_best) if b]
        best_vals = [v for v, b in zip(values, is_best) if b]
        if best_iters:
            ax.scatter(best_iters, best_vals, c=COLORS["best"], s=30, zorder=5)

        ax.set_xlabel("Iteration")
        ax.set_ylabel(param_name)
        ax.set_title(param_name)
        ax.grid(True, alpha=0.3)

    # Hide empty subplots
    for idx in range(n_params, len(axes)):
        axes[idx].set_visible(False)

    fig_params.suptitle("Parameter Evolution", fontsize=12, fontweight="bold")
    fig_params.tight_layout()
    fig_params.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig_params.get_facecolor())
    plt.close(fig_params)


def create_exploration_summary(
    exploration: Dict,
    grid_results: Optional[Dict],
    histories: Dict[str, Dict],
    output_path: Path,
) -> None:
    """Create multi-panel summary figure."""
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.25)

    fig.suptitle(
        "JEE Exploration Summary\n"
        f"Best SSE: {exploration.get('best_sse', 0):,.0f} | "
        f"Method: {exploration.get('best_method', 'N/A')} | "
        f"Improvement: {exploration.get('improvement_from_baseline', 0):.1f}%",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    # Panel 1: Grid search overview
    ax1 = fig.add_subplot(gs[0, 0])
    if grid_results:
        plot_grid_search_overview(ax1, grid_results, exploration)
    else:
        ax1.text(0.5, 0.5, "Grid results not available", ha="center", va="center", transform=ax1.transAxes)
        ax1.set_title("Grid Search")

    # Panel 2: Method comparison
    ax2 = fig.add_subplot(gs[0, 1])
    plot_method_comparison(ax2, exploration)

    # Panel 3: Improvement breakdown
    ax3 = fig.add_subplot(gs[1, 0])
    plot_improvement_breakdown(ax3, exploration)

    # Panel 4: Convergence curves
    ax4 = fig.add_subplot(gs[1, 1])
    plot_convergence_curves(ax4, histories)

    # Panel 5: Summary statistics
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.axis("off")

    summary_text = f"""
EXPLORATION SUMMARY
{'=' * 40}

Grid Search:
  Points evaluated: {exploration.get('grid_points_evaluated', 0)}
  Best grid SSE: {exploration.get('grid_best_sse', 0):,.0f}

Parallel Optimization:
  Runs completed: {len(exploration.get('local_opt_results', []))}
  Best method: {exploration.get('best_method', 'N/A')}
  Best starting rank: {exploration.get('best_starting_rank', 0)}

Overall Results:
  Baseline SSE: {exploration.get('baseline_sse', 0):,.0f}
  Best SSE: {exploration.get('best_sse', 0):,.0f}
  Improvement from baseline: {exploration.get('improvement_from_baseline', 0):.1f}%
  Improvement from grid: {exploration.get('improvement_from_grid', 0):.1f}%
  Within footprint: {'YES' if exploration.get('within_footprint', False) else 'NO'}
"""
    ax5.text(
        0.05, 0.95, summary_text, transform=ax5.transAxes,
        fontsize=10, fontfamily="monospace", verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.1)
    )

    # Panel 6: Best parameters
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.axis("off")

    best_params = exploration.get("best_params", {})
    params_text = "BEST PARAMETERS\n" + "=" * 40 + "\n\n"
    for k, v in best_params.items():
        params_text += f"  {k}: {v:.6f}\n"

    ax6.text(
        0.05, 0.95, params_text, transform=ax6.transAxes,
        fontsize=10, fontfamily="monospace", verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.1)
    )

    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def create_visualization_report(
    results_dir: Path,
    output_dir: Optional[Path] = None,
    style: str = "dark",
) -> List[Path]:
    """
    Create all visualization figures from exploration results.

    Args:
        results_dir: Directory containing exploration_result.json
        output_dir: Where to save figures (default: results_dir/figures)
        style: "dark" or "light" theme

    Returns:
        List of generated figure paths
    """
    results_dir = Path(results_dir)
    output_dir = output_dir or results_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set style
    if style == "dark":
        setup_dark_style()
    else:
        setup_light_style()

    # Load data
    exploration, grid_results = load_exploration_results(results_dir)
    histories = load_iteration_histories(results_dir)

    generated = []

    # 1. Grid search overview (if available)
    if grid_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        plot_grid_search_overview(ax, grid_results, exploration)
        path = output_dir / "grid_search_overview.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        generated.append(path)
        print(f"  Created: {path.name}")

    # 2. Method comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_method_comparison(ax, exploration)
    path = output_dir / "method_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    generated.append(path)
    print(f"  Created: {path.name}")

    # 3. Improvement breakdown
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_improvement_breakdown(ax, exploration)
    path = output_dir / "improvement_breakdown.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    generated.append(path)
    print(f"  Created: {path.name}")

    # 4. Convergence curves
    if histories:
        fig, ax = plt.subplots(figsize=(12, 6))
        plot_convergence_curves(ax, histories)
        path = output_dir / "convergence_curves.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        generated.append(path)
        print(f"  Created: {path.name}")

    # 5. Parameter evolution for each run (if histories have params)
    opt_details_dir = output_dir / "opt_details"
    for run_id, data in histories.items():
        history = data.get("history", [])
        if history and "params" in history[0]:
            opt_details_dir.mkdir(exist_ok=True)
            path = opt_details_dir / f"{run_id}_params.png"
            fig = plt.figure()
            plot_parameter_evolution(fig, data, path)
            generated.append(path)
            print(f"  Created: opt_details/{path.name}")

    # 6. Summary figure
    path = output_dir / "exploration_summary.png"
    create_exploration_summary(exploration, grid_results, histories, path)
    generated.append(path)
    print(f"  Created: {path.name}")

    return generated


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize JEE exploration results"
    )
    parser.add_argument(
        "--results", "-r", type=Path, required=True,
        help="Path to exploration results directory"
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output directory for figures (default: results_dir/figures)"
    )
    parser.add_argument(
        "--style", "-s", choices=["dark", "light"], default="dark",
        help="Plot style (default: dark)"
    )

    args = parser.parse_args()

    results_dir = args.results
    if results_dir.is_file():
        results_dir = results_dir.parent

    print(f"Loading results from: {results_dir}")

    try:
        figure_paths = create_visualization_report(
            results_dir=results_dir,
            output_dir=args.output,
            style=args.style,
        )
        print(f"\nGenerated {len(figure_paths)} figures")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        raise

    return 0


if __name__ == "__main__":
    exit(main())
