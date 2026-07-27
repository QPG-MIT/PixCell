"""
Visualization Module for HOMI Explorer

Provides matplotlib-based polygon rendering with hole support.
Adapted from Weber for embedded use in the main HOMI app.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.lines import Line2D
import numpy as np
from typing import Dict, Tuple, Optional, List, Any

import gdsfactory as gf

from .theme import LAYER_COLORS, get_layer_color, COLORS


def get_default_layer_colors() -> Dict[Tuple[int, int], Dict[str, str]]:
    """
    Get default layer colors from theme.

    Returns:
        Dict mapping layer tuples to color dicts with 'face', 'edge', 'name' keys
    """
    return {
        layer: {
            'face': info['face'],
            'edge': info['edge'],
            'name': info['name']
        }
        for layer, info in LAYER_COLORS.items()
    }


# Default layer colors (from theme)
DEFAULT_LAYER_COLORS = get_default_layer_colors()


def get_component_bbox(component: gf.Component) -> Tuple[float, float, float, float]:
    """
    Get bounding box from component, handling different gdsfactory versions.

    Returns:
        (xmin, ymin, xmax, ymax)
    """
    bbox = component.bbox()

    try:
        xmin, ymin = bbox[0]
        xmax, ymax = bbox[1]
    except TypeError:
        xmin, ymin = bbox.left, bbox.bottom
        xmax, ymax = bbox.right, bbox.top

    return float(xmin), float(ymin), float(xmax), float(ymax)


def render_component_polygons(
    ax: plt.Axes,
    component: gf.Component,
    layer_colors: Optional[Dict[Tuple[int, int], Dict[str, str]]] = None,
    alpha: float = 0.9
) -> Tuple[bool, List[np.ndarray], Dict[Tuple[int, int], str]]:
    """
    Render component polygons to a matplotlib axes.

    Args:
        ax: Matplotlib axes to render to
        component: GDSFactory component
        layer_colors: Optional dict mapping layer tuples to color dicts
        alpha: Polygon transparency

    Returns:
        Tuple of (polygons_rendered, hole_outlines, plotted_layers)
    """
    if layer_colors is None:
        layer_colors = DEFAULT_LAYER_COLORS

    default_color = {'face': '#888888', 'edge': '#666666', 'name': 'Device'}
    polygons_rendered = False
    hole_outlines = []
    plotted_layers = {}

    try:
        polys = component.get_polygons()
        if isinstance(polys, dict):
            for layer, poly_list in polys.items():
                # Normalize layer key
                if isinstance(layer, tuple):
                    layer_tuple = layer
                elif isinstance(layer, int):
                    layer_tuple = (layer, 0)
                else:
                    layer_tuple = (1, 0)

                colors = layer_colors.get(layer_tuple, default_color)
                plotted_layers[layer_tuple] = colors.get('name', f'Layer {layer_tuple}')

                for poly in poly_list:
                    vertices = []
                    codes = []

                    # Get hull (outer boundary)
                    hull_pts = []
                    for pt in poly.each_point_hull():
                        hull_pts.append((pt.x / 1000, pt.y / 1000))  # nm to um

                    if hull_pts:
                        # Add outer contour
                        for i, pt in enumerate(hull_pts):
                            vertices.append(pt)
                            codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                        vertices.append(hull_pts[0])
                        codes.append(Path.CLOSEPOLY)

                        # Check for holes
                        try:
                            num_holes = poly.holes()
                            for hole_idx in range(num_holes):
                                hole_pts = []
                                for pt in poly.each_point_hole(hole_idx):
                                    hole_pts.append((pt.x / 1000, pt.y / 1000))

                                if hole_pts:
                                    # Add hole to path
                                    for i, pt in enumerate(hole_pts):
                                        vertices.append(pt)
                                        codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                                    vertices.append(hole_pts[0])
                                    codes.append(Path.CLOSEPOLY)

                                    # Draw hole outline
                                    hole_arr = np.array(hole_pts + [hole_pts[0]])
                                    ax.plot(hole_arr[:, 0], hole_arr[:, 1],
                                           color='#FF6B6B', linewidth=2.5, linestyle='-',
                                           zorder=10)
                                    hole_outlines.append(hole_arr)
                        except Exception:
                            pass

                        # Create the path with holes
                        path = Path(vertices, codes)
                        patch = PathPatch(path, facecolor=colors['face'],
                                        edgecolor=colors['edge'],
                                        linewidth=1.5, alpha=alpha)
                        ax.add_patch(patch)
                        polygons_rendered = True

    except Exception as e:
        pass  # Will fall back to bounding box

    return polygons_rendered, hole_outlines, plotted_layers


def create_device_figure(
    component: gf.Component,
    layer_colors: Optional[Dict[Tuple[int, int], Dict[str, str]]] = None,
    target_footprint: Optional[Dict[str, float]] = None,
    figsize: Tuple[int, int] = (12, 8),
    title: Optional[str] = None
) -> plt.Figure:
    """
    Create a complete figure with device visualization.

    Args:
        component: GDSFactory component to render
        layer_colors: Optional layer color mapping
        target_footprint: Optional dict with 'width_um' and 'height_um'
        figsize: Figure size tuple
        title: Optional figure title

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Render polygons
    polygons_rendered, hole_outlines, plotted_layers = render_component_polygons(
        ax, component, layer_colors
    )

    # Get bounding box
    xmin, ymin, xmax, ymax = get_component_bbox(component)
    gds_width = xmax - xmin
    gds_height = ymax - ymin
    gds_cx = (xmin + xmax) / 2
    gds_cy = (ymin + ymax) / 2

    # Fallback if no polygons rendered
    if not polygons_rendered:
        ax.add_patch(mpatches.Rectangle(
            (xmin, ymin), gds_width, gds_height,
            linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.5,
            label='Device bounds'
        ))

    # Draw target footprint if provided
    legend_elements = []

    if target_footprint:
        target_w = target_footprint.get("width_um", 5.5)
        target_h = target_footprint.get("height_um", 3.0)

        target_rect = mpatches.Rectangle(
            (gds_cx - target_w / 2, gds_cy - target_h / 2),
            target_w, target_h,
            linewidth=3, edgecolor='green', facecolor='none',
            linestyle='--'
        )
        ax.add_patch(target_rect)

        legend_elements.append(Line2D([0], [0], color='green', linewidth=3, linestyle='--',
                                     label=f'Target: {target_w}x{target_h} um'))

    # Build legend from plotted layers
    if layer_colors is None:
        layer_colors = DEFAULT_LAYER_COLORS

    for layer_tuple, layer_name in sorted(plotted_layers.items()):
        colors = layer_colors.get(layer_tuple, {'face': '#888888'})
        legend_elements.insert(0, mpatches.Patch(
            facecolor=colors['face'],
            edgecolor=colors.get('edge', colors['face']),
            label=layer_name
        ))

    if hole_outlines:
        legend_elements.append(Line2D([0], [0], color='#FF6B6B', linewidth=2.5,
                                     label='Holes (cutouts)'))

    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

    # Axis setup
    pad = 0.5
    x_bounds = [xmin, xmax]
    y_bounds = [ymin, ymax]

    if target_footprint:
        x_bounds.extend([gds_cx - target_footprint.get("width_um", 0) / 2,
                        gds_cx + target_footprint.get("width_um", 0) / 2])
        y_bounds.extend([gds_cy - target_footprint.get("height_um", 0) / 2,
                        gds_cy + target_footprint.get("height_um", 0) / 2])

    ax.set_xlim(min(x_bounds) - pad, max(x_bounds) + pad)
    ax.set_ylim(min(y_bounds) - pad, max(y_bounds) + pad)

    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")

    if title:
        ax.set_title(title, fontsize=12)
    else:
        ax.set_title(f"Device: {gds_width:.2f} x {gds_height:.2f} um", fontsize=12)

    ax.set_facecolor('#f8f9fa')

    return fig


def create_tts_figure(
    trajectories: np.ndarray,
    seeds: int,
    turns: int,
    figsize: Tuple[int, int] = (12, 4)
) -> plt.Figure:
    """
    Create test-time scaling visualization.

    Shows seed trajectories and final IoU distribution.

    Args:
        trajectories: Array of shape (seeds, turns) with IoU values
        seeds: Number of seeds
        turns: Number of turns
        figsize: Figure size tuple

    Returns:
        matplotlib Figure with two subplots
    """
    best_at_t = np.max(trajectories, axis=0)
    mean_at_t = np.mean(trajectories, axis=0)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Left: Individual trajectories
    cmap = plt.colormaps.get_cmap('viridis')
    seed_quality = np.max(trajectories, axis=1)
    seed_quality_norm = (seed_quality - seed_quality.min()) / (seed_quality.max() - seed_quality.min() + 1e-6)

    for idx in range(seeds):
        axes[0].plot(range(1, turns + 1), trajectories[idx],
                     alpha=0.5, color=cmap(seed_quality_norm[idx]), linewidth=1)
    axes[0].plot(range(1, turns + 1), best_at_t, 'r-', linewidth=2.5, label='Best@T')
    axes[0].plot(range(1, turns + 1), mean_at_t, 'b--', linewidth=2, label='Mean')
    axes[0].set_xlabel('Turn')
    axes[0].set_ylabel('IoU')
    axes[0].set_title(f'Test-Time Scaling ({seeds} seeds)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(0, 0.9)

    # Right: Final IoU distribution
    final_ious = trajectories[:, -1]
    axes[1].hist(final_ious, bins=10, edgecolor='black', alpha=0.7, color='steelblue')
    axes[1].axvline(final_ious.mean(), color='red', linestyle='--', label=f'Mean: {final_ious.mean():.2f}')
    axes[1].axvline(np.max(final_ious), color='green', linestyle='-', label=f'Best: {np.max(final_ious):.2f}')
    axes[1].set_xlabel('Final IoU')
    axes[1].set_ylabel('Count')
    axes[1].set_title('Seed Distribution (Final Turn)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def create_sketch_analysis_figure(
    original_img: np.ndarray,
    binary_img: np.ndarray,
    components: List[Dict[str, Any]],
    scale: float = 1.0,
    figsize: Tuple[int, int] = (14, 4)
) -> plt.Figure:
    """
    Create sketch analysis visualization.

    Shows original, binary threshold, and detected components overlay.

    Args:
        original_img: Original grayscale image
        binary_img: Binary thresholded image
        components: List of detected component dicts
        scale: Scale factor for component dimensions
        figsize: Figure size tuple

    Returns:
        matplotlib Figure with three subplots
    """
    from matplotlib.patches import Rectangle, Circle

    fig, axes = plt.subplots(1, 3, figsize=figsize)

    # Original sketch
    axes[0].imshow(original_img, cmap='gray')
    axes[0].set_title('Original Sketch')
    axes[0].axis('off')

    # Binary threshold
    axes[1].imshow(binary_img, cmap='gray')
    axes[1].set_title('Binary Threshold')
    axes[1].axis('off')

    # Detected components overlay
    axes[2].imshow(original_img, cmap='gray', alpha=0.5)

    colors_vis = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    for i, comp in enumerate(components):
        color = colors_vis[i % len(colors_vis)]
        cx, cy = comp.get('center', (0, 0))

        if comp['type'] == 'ring':
            radius_px = comp['radius'] / scale
            circle = Circle((cx, cy), radius_px, fill=False,
                           edgecolor=color, linewidth=2, linestyle='--')
            axes[2].add_patch(circle)
            axes[2].annotate(f"Ring\nr={comp['radius']}μm",
                            (cx, cy), color=color, fontsize=9,
                            ha='center', va='center',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        else:
            w = comp.get('length', comp.get('width', 10)) / scale
            h = comp.get('width', comp.get('width1', 5)) / scale
            rect = Rectangle((cx - w/2, cy - h/2), w, h, fill=False,
                            edgecolor=color, linewidth=2, linestyle='--')
            axes[2].add_patch(rect)
            label = f"{comp['type']}"
            axes[2].annotate(label, (cx, cy - h/2 - 10), color=color,
                            fontsize=9, ha='center',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    axes[2].set_title('Detected Components')
    axes[2].axis('off')

    plt.tight_layout()
    return fig


def create_trident_benchmark_figure(
    models: List[str],
    turn1_iou: List[float],
    best_iou: List[float],
    best_turn: List[int],
    figsize: Tuple[int, int] = (10, 5)
) -> plt.Figure:
    """
    Create Trident benchmark comparison visualization with side-by-side bars.

    Shows Turn-1 IoU vs Best IoU for multiple models with value labels.

    Args:
        models: List of model names
        turn1_iou: Turn-1 IoU values
        best_iou: Best IoU values
        best_turn: Best turn number for each model
        figsize: Figure size tuple

    Returns:
        matplotlib Figure with grouped bar chart
    """
    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=figsize)
    bars1 = ax.bar(x - width/2, turn1_iou, width, label='Turn 1 IoU', color='#4A90D9', edgecolor='black')
    bars2 = ax.bar(x + width/2, best_iou, width, label='Best@T IoU', color='#50C878', edgecolor='black')

    ax.set_xlabel('Model')
    ax.set_ylabel(r'$\text{IoU} = |G \cap \hat{G}| / |G \cup \hat{G}|$ [0,1]')
    ax.set_title(r'Trident Benchmark: $\text{IoU} = |G \cap \hat{G}| / |G \cup \hat{G}|$')
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=9)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 0.8)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    for idx, bar in enumerate(bars2):
        height = bar.get_height()
        ax.annotate(f'{height:.2f}\n(T{best_turn[idx]})',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    return fig


def create_benchmark_figure(
    models: List[str],
    turn1_iou: List[float],
    best_iou: List[float],
    figsize: Tuple[int, int] = (14, 5)
) -> plt.Figure:
    """
    Create benchmark comparison visualization.

    Shows Turn-1 IoU vs Best IoU for multiple models.

    Args:
        models: List of model names
        turn1_iou: Turn-1 IoU values
        best_iou: Best IoU values
        figsize: Figure size tuple

    Returns:
        matplotlib Figure with two subplots
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    x = np.arange(len(models))
    width = 0.35

    # Left: Turn-1 IoU
    axes[0].bar(x, turn1_iou, width, color='steelblue', edgecolor='black')
    axes[0].set_xlabel('Model')
    axes[0].set_ylabel('IoU')
    axes[0].set_title('Turn-1 IoU (Initial Generation)')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(models, rotation=45, ha='right')
    axes[0].set_ylim(0, 1)
    axes[0].grid(True, alpha=0.3, axis='y')

    # Right: Best IoU
    axes[1].bar(x, best_iou, width, color='forestgreen', edgecolor='black')
    axes[1].set_xlabel('Model')
    axes[1].set_ylabel('IoU')
    axes[1].set_title('Best IoU (After Multi-turn)')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(models, rotation=45, ha='right')
    axes[1].set_ylim(0, 1)
    axes[1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    return fig


def create_gallery_benchmark_figure(
    models: List[str],
    primitive_rates: List[float],
    mean_ious: List[float],
    expected_usable: List[float],
    figsize: Tuple[int, int] = (14, 5)
) -> plt.Figure:
    """
    Create gallery benchmark visualization with scatter and ranking plots.

    Args:
        models: List of model names
        primitive_rates: Primitive detection rates (%)
        mean_ious: Mean IoU values
        expected_usable: Expected usable IoU values
        figsize: Figure size tuple

    Returns:
        matplotlib Figure with two subplots
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Left: Primitive Rate vs Mean IoU
    scatter = axes[0].scatter(primitive_rates, mean_ious, c=expected_usable,
                              cmap='RdYlGn', s=200, edgecolors='black', linewidth=1.5)
    for i, model in enumerate(models):
        axes[0].annotate(model.replace('\n', ' '), (primitive_rates[i], mean_ious[i]),
                        textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8)
    axes[0].set_xlabel('Primitive Rate (%)', fontsize=11)
    axes[0].set_ylabel(r'$\bar{\text{IoU}}_{\text{prim}} = \frac{1}{N}\sum_{i=1}^{N}\text{IoU}_i$ [0,1]', fontsize=11)
    axes[0].set_title(r'Model Performance: $R_{\text{prim}}$ vs $\bar{\text{IoU}}$', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(20, 95)
    axes[0].set_ylim(0.1, 0.5)
    cbar = plt.colorbar(scatter, ax=axes[0])
    cbar.set_label('Expected Usable IoU', fontsize=10)

    # Right: Expected Usable IoU ranking
    sorted_indices = np.argsort(expected_usable)[::-1]
    sorted_models = [models[i].replace('\n', ' ') for i in sorted_indices]
    sorted_usable = [expected_usable[i] for i in sorted_indices]
    bar_colors = plt.cm.RdYlGn(np.linspace(0.8, 0.2, len(models)))

    bars = axes[1].barh(sorted_models, sorted_usable,
                        color=[bar_colors[i] for i in range(len(sorted_models))],
                        edgecolor='black')
    axes[1].set_xlabel('Expected Usable IoU', fontsize=11)
    axes[1].set_title(r'Model Ranking: $\mathbb{E}[\text{IoU}_{\text{usable}}] = R_{\text{prim}} \cdot \bar{\text{IoU}}$', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='x')

    # Add value labels
    for bar, val in zip(bars, sorted_usable):
        axes[1].text(val + 0.01, bar.get_y() + bar.get_height()/2, f'{val:.3f}',
                    va='center', fontsize=9)

    plt.tight_layout()
    return fig
