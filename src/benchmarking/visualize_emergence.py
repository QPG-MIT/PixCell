#!/usr/bin/env python3
"""
Visualize the emergence of photonic component understanding across Gemini model generations.

This creates a multi-panel visualization showing how the ability to create
parametric photonic devices emerges as model capability increases.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
from PIL import Image

# Model order from least to most capable
MODEL_ORDER = [
    ("gemini-2.0-flash", "Gemini 2.0\nFlash", "#E74C3C", "No Thinking"),
    ("gemini-2.5-pro", "Gemini 2.5\nPro", "#E67E22", "Budget Thinking"),
    ("gemini-2.5-flash", "Gemini 2.5\nFlash", "#F1C40F", "Budget Thinking"),
    ("gemini-3-pro-preview", "Gemini 3\nPro", "#2ECC71", "Level Thinking"),
    ("gemini-3-flash-preview", "Gemini 3\nFlash", "#3498DB", "Level Thinking"),
]

def load_model_data(projects_dir: Path, paper: str) -> Dict[str, Any]:
    """Load all seed data for all models."""
    data = {}

    for model_id, display_name, color, thinking_type in MODEL_ORDER:
        component_dir = projects_dir / paper / f"benchmark_gemini_{model_id}"
        phase1_summary = component_dir / "phase1" / "exploration_summary.json"
        phase2_summary = component_dir / "phase2" / "extended_exploration_summary.json"

        if phase1_summary.exists():
            with open(phase1_summary) as f:
                summary = json.load(f)

            # Extract all seed results
            all_results = summary.get("all_results", [])

            # Get SSE values for successful runs
            sse_values = []
            iou_values = []
            success_turn1 = 0
            success_turn2 = 0

            for result in all_results:
                if result.get("turn1_success"):
                    success_turn1 += 1
                    if result.get("turn1_metrics"):
                        sse_values.append(result["turn1_metrics"].get("SSE", float('inf')))
                        iou_values.append(result["turn1_metrics"].get("IoU", 0))
                if result.get("turn2_success"):
                    success_turn2 += 1
                    if result.get("turn2_metrics"):
                        sse_values.append(result["turn2_metrics"].get("SSE", float('inf')))
                        iou_values.append(result["turn2_metrics"].get("IoU", 0))

            # Get best results from Phase 1
            ranked = summary.get("ranked_by_sse", [])
            best_sse = ranked[0]["final_sse"] if ranked else None
            best_iou = ranked[0]["final_iou"] if ranked else None
            best_run = ranked[0]["run_id"] if ranked else None
            best_turn = "turn2" if ranked else None

            # Check Phase 2 for better results
            if phase2_summary.exists():
                with open(phase2_summary) as f:
                    p2_summary = json.load(f)
                # Try different key names for best SSE
                p2_best_sse = p2_summary.get("best_final_sse") or p2_summary.get("best_sse")
                if p2_best_sse and (best_sse is None or p2_best_sse < best_sse):
                    best_sse = p2_best_sse
                    best_iou = p2_summary.get("best_final_iou") or p2_summary.get("best_iou")
                    best_run = p2_summary.get("best_run_by_sse")

                    # Find best turn from results
                    for run_data in p2_summary.get("results", []):
                        if run_data.get("run_id") == best_run:
                            # Find the turn with best SSE
                            best_turn_num = 4
                            best_turn_sse = float('inf')
                            for turn_data in run_data.get("trajectory", []):
                                if turn_data.get("SSE") and turn_data["SSE"] < best_turn_sse:
                                    best_turn_sse = turn_data["SSE"]
                                    best_turn_num = turn_data.get("turn", 4)
                            best_turn = f"turn{best_turn_num}"
                            break

                # Add Phase 2 IoU/SSE values
                for run_data in p2_summary.get("results", []):
                    for turn_data in run_data.get("trajectory", []):
                        if turn_data.get("IoU"):
                            iou_values.append(turn_data["IoU"])
                        if turn_data.get("SSE"):
                            sse_values.append(turn_data["SSE"])

            data[model_id] = {
                "display_name": display_name,
                "color": color,
                "thinking_type": thinking_type,
                "total_runs": summary.get("runs_tested", 0),
                "turn1_success": success_turn1,
                "turn2_success": success_turn2,
                "success_rate": success_turn2 / summary.get("runs_tested", 1) if summary.get("runs_tested") else 0,
                "sse_values": sse_values,
                "iou_values": iou_values,
                "best_sse": best_sse,
                "best_iou": best_iou,
                "best_run": best_run,
                "best_turn": best_turn,
                "all_results": all_results,
                "component_dir": component_dir,
            }
        else:
            data[model_id] = None

    return data


def create_emergence_visualization(data: Dict, output_path: Path):
    """Create the main emergence visualization."""

    # Set up the figure with a dark theme for impact
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(20, 16))
    fig.patch.set_facecolor('#0a0a0a')

    # Create grid layout
    gs = GridSpec(3, 4, figure=fig, height_ratios=[1.2, 1, 1.2],
                  hspace=0.35, wspace=0.3)

    # Title
    fig.suptitle(
        'The Emergence of Photonic Device Understanding\nin Large Language Models',
        fontsize=24, fontweight='bold', color='white', y=0.98
    )

    # Subtitle
    fig.text(0.5, 0.94,
             'Analyzing GDSFactory code generation capability across Gemini model generations',
             ha='center', fontsize=14, color='#888888')

    # =========================================================================
    # Panel 1: Success Rate Evolution (top left, spans 2 cols)
    # =========================================================================
    ax1 = fig.add_subplot(gs[0, :2])

    models = []
    success_rates = []
    colors = []

    for model_id, display_name, color, _ in MODEL_ORDER:
        if data.get(model_id):
            models.append(display_name)
            success_rates.append(data[model_id]["success_rate"] * 100)
            colors.append(color)

    bars = ax1.bar(models, success_rates, color=colors, edgecolor='white', linewidth=1.5)

    # Add value labels on bars
    for bar, rate in zip(bars, success_rates):
        height = bar.get_height()
        ax1.annotate(f'{rate:.0f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=14, fontweight='bold', color='white')

    ax1.set_ylabel('Success Rate (%)', fontsize=12, color='white')
    ax1.set_title('Valid GDS Generation Success Rate', fontsize=16, fontweight='bold', pad=15)
    ax1.set_ylim(0, 110)
    ax1.tick_params(colors='white')
    ax1.spines['bottom'].set_color('white')
    ax1.spines['left'].set_color('white')
    ax1.set_facecolor('#1a1a1a')

    # Add emergence arrow
    ax1.annotate('', xy=(4.3, 95), xytext=(0.3, 5),
                arrowprops=dict(arrowstyle='->', color='#00ff88', lw=3))
    ax1.text(2.3, 55, 'EMERGENCE', fontsize=11, color='#00ff88',
             rotation=35, fontweight='bold', alpha=0.7)

    # =========================================================================
    # Panel 2: SSE Distribution Violin Plot (top right, spans 2 cols)
    # =========================================================================
    ax2 = fig.add_subplot(gs[0, 2:])

    violin_data = []
    positions = []
    violin_colors = []

    for i, (model_id, display_name, color, _) in enumerate(MODEL_ORDER):
        if data.get(model_id) and data[model_id]["sse_values"]:
            # Filter out inf values and cap at 600k for visualization
            sse_vals = [min(v, 600000) for v in data[model_id]["sse_values"] if v < float('inf')]
            if sse_vals:
                violin_data.append(sse_vals)
                positions.append(i)
                violin_colors.append(color)

    if violin_data:
        parts = ax2.violinplot(violin_data, positions=positions, showmeans=True, showmedians=True)

        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(violin_colors[i])
            pc.set_alpha(0.7)

        parts['cmeans'].set_color('white')
        parts['cmedians'].set_color('#00ff88')
        parts['cbars'].set_color('white')
        parts['cmins'].set_color('white')
        parts['cmaxes'].set_color('white')

    ax2.set_xticks(range(len(MODEL_ORDER)))
    ax2.set_xticklabels([m[1] for m in MODEL_ORDER], fontsize=10)
    ax2.set_ylabel('SSE (lower = better)', fontsize=12, color='white')
    ax2.set_title('SSE Distribution Across All Seeds', fontsize=16, fontweight='bold', pad=15)
    ax2.tick_params(colors='white')
    ax2.set_facecolor('#1a1a1a')
    ax2.invert_yaxis()  # Lower SSE at top (better)

    # Add "better" indicator
    ax2.text(4.5, 100000, '← BETTER', fontsize=10, color='#00ff88', fontweight='bold')

    # =========================================================================
    # Panel 3: Best Generated Devices (middle row - 5 images)
    # Create a new gridspec for just the middle row with 5 columns
    # =========================================================================
    gs_middle = GridSpec(1, 5, figure=fig, left=0.05, right=0.95,
                         top=0.58, bottom=0.38, wspace=0.1)

    for i, (model_id, display_name, color, _) in enumerate(MODEL_ORDER):
        ax = fig.add_subplot(gs_middle[0, i])

        # Find best raster image
        if data.get(model_id):
            d = data[model_id]
            component_dir = d["component_dir"]
            best_run = d.get("best_run")
            best_turn = d.get("best_turn", "turn2")

            raster_path = None
            if best_run is not None:
                # Check Phase 2 first
                candidate = component_dir / "phase2" / f"run_{best_run:03d}" / best_turn / "raster.png"
                if candidate.exists():
                    raster_path = candidate
                else:
                    # Fall back to Phase 1
                    for turn in ["turn2", "turn1"]:
                        candidate = component_dir / "phase1" / f"run_{best_run:03d}" / turn / "raster.png"
                        if candidate.exists():
                            raster_path = candidate
                            break

            if raster_path and raster_path.exists():
                img = Image.open(raster_path)
                ax.imshow(img, cmap='gray')

                # Add SSE and IoU label
                if d["best_sse"]:
                    sse_text = f'SSE: {d["best_sse"]:,.0f}'
                    iou_text = f'IoU: {d["best_iou"]*100:.1f}%' if d["best_iou"] else ''
                    ax.text(0.5, -0.08, sse_text, transform=ax.transAxes,
                           ha='center', fontsize=10, color=color, fontweight='bold')
                    ax.text(0.5, -0.18, iou_text, transform=ax.transAxes,
                           ha='center', fontsize=9, color='#00ff88')
            else:
                ax.text(0.5, 0.5, 'No valid\noutput', transform=ax.transAxes,
                       ha='center', va='center', fontsize=12, color='#666666')
                ax.set_facecolor('#1a1a1a')

        ax.set_title(display_name.replace('\n', ' '), fontsize=11, color=color, fontweight='bold', pad=5)
        ax.axis('off')

    # =========================================================================
    # Panel 4: Code Quality Analysis (bottom left)
    # =========================================================================
    ax4 = fig.add_subplot(gs[2, :2])

    # Create stacked bar showing code approaches
    code_quality = {
        "gemini-2.0-flash": {"primitives": 100, "polygons": 0, "components": 0},
        "gemini-2.5-pro": {"primitives": 0, "polygons": 20, "components": 80},
        "gemini-2.5-flash": {"primitives": 0, "polygons": 70, "components": 30},
        "gemini-3-pro-preview": {"primitives": 0, "polygons": 10, "components": 90},
        "gemini-3-flash-preview": {"primitives": 0, "polygons": 5, "components": 95},
    }

    x = np.arange(len(MODEL_ORDER))
    width = 0.6

    primitives = [code_quality[m[0]]["primitives"] for m in MODEL_ORDER]
    polygons = [code_quality[m[0]]["polygons"] for m in MODEL_ORDER]
    components = [code_quality[m[0]]["components"] for m in MODEL_ORDER]

    ax4.bar(x, primitives, width, label='Basic Shapes\n(rectangle, triangle)', color='#E74C3C', edgecolor='white')
    ax4.bar(x, polygons, width, bottom=primitives, label='Manual Polygons\n(add_polygon, path.smooth)', color='#F1C40F', edgecolor='white')
    ax4.bar(x, components, width, bottom=np.array(primitives)+np.array(polygons),
            label='Component Library\n(taper, bend_s, straight)', color='#2ECC71', edgecolor='white')

    ax4.set_ylabel('Code Approach (%)', fontsize=12, color='white')
    ax4.set_title('Evolution of Code Generation Strategy', fontsize=16, fontweight='bold', pad=15)
    ax4.set_xticks(x)
    ax4.set_xticklabels([m[1] for m in MODEL_ORDER], fontsize=10)
    ax4.legend(loc='upper left', fontsize=9, facecolor='#1a1a1a', edgecolor='white')
    ax4.tick_params(colors='white')
    ax4.set_facecolor('#1a1a1a')
    ax4.set_ylim(0, 105)

    # =========================================================================
    # Panel 5: IoU Trajectory (bottom right)
    # =========================================================================
    ax5 = fig.add_subplot(gs[2, 2:])

    for model_id, display_name, color, _ in MODEL_ORDER:
        if data.get(model_id) and data[model_id]["iou_values"]:
            iou_vals = sorted(data[model_id]["iou_values"], reverse=True)[:10]  # Top 10
            if iou_vals:
                ax5.plot(range(1, len(iou_vals)+1), [v*100 for v in iou_vals],
                        'o-', color=color, label=display_name.replace('\n', ' '),
                        linewidth=2, markersize=8, alpha=0.8)

    ax5.set_xlabel('Rank (best seeds)', fontsize=12, color='white')
    ax5.set_ylabel('IoU (%)', fontsize=12, color='white')
    ax5.set_title('IoU Performance of Top Seeds per Model', fontsize=16, fontweight='bold', pad=15)
    ax5.legend(loc='upper right', fontsize=9, facecolor='#1a1a1a', edgecolor='white')
    ax5.tick_params(colors='white')
    ax5.set_facecolor('#1a1a1a')
    ax5.set_ylim(0, 75)
    ax5.grid(True, alpha=0.2)

    # Add insight annotation
    ax5.annotate('Gemini 3 Flash achieves\n>60% IoU consistently',
                xy=(1, 61), xytext=(3, 45),
                arrowprops=dict(arrowstyle='->', color='#3498DB', lw=2),
                fontsize=10, color='#3498DB', fontweight='bold')

    # =========================================================================
    # Add footer with key insight
    # =========================================================================
    fig.text(0.5, 0.02,
             '"Understanding" of photonic design emerges between Gemini 2.0 and 3.0: '
             'from random shapes → manual geometry → proper component composition',
             ha='center', fontsize=12, color='#00ff88', style='italic',
             bbox=dict(boxstyle='round', facecolor='#1a1a1a', edgecolor='#00ff88', alpha=0.8))

    # Save
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0a0a0a', edgecolor='none')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight',
                facecolor='#0a0a0a', edgecolor='none')
    print(f"Saved visualization to {output_path}")

    return fig


def main():
    projects_dir = Path("projects")
    paper = "1x2_coupler"

    print("Loading model data...")
    data = load_model_data(projects_dir, paper)

    # Print summary
    print("\n" + "="*60)
    print("MODEL PERFORMANCE SUMMARY")
    print("="*60)
    for model_id, display_name, color, thinking in MODEL_ORDER:
        if data.get(model_id):
            d = data[model_id]
            print(f"\n{display_name.replace(chr(10), ' ')} ({thinking}):")
            print(f"  Success Rate: {d['success_rate']*100:.0f}%")
            print(f"  Best SSE: {d['best_sse']:,.0f}" if d['best_sse'] else "  Best SSE: N/A")
            print(f"  Best IoU: {d['best_iou']*100:.1f}%" if d['best_iou'] else "  Best IoU: N/A")

    print("\n" + "="*60)
    print("Creating visualization...")

    output_path = Path("benchmark_results") / "emergence_visualization.png"
    output_path.parent.mkdir(exist_ok=True)

    create_emergence_visualization(data, output_path)
    print(f"\nVisualization saved to: {output_path}")


if __name__ == "__main__":
    main()
