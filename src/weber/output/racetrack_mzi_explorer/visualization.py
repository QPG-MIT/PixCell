"""
Visualization Module for Weber Explorers

Provides matplotlib-based polygon rendering with hole support.
Extracted from modular_explorer/app.py for reuse.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.lines import Line2D
import numpy as np
from typing import Dict, Tuple, Optional, List, Any
import gdsfactory as gf


# Default layer colors
DEFAULT_LAYER_COLORS = {
    (1, 0): {'face': '#2E86AB', 'edge': '#1B4965', 'name': 'Layer 1'},
    (2, 0): {'face': '#F4A261', 'edge': '#E76F51', 'name': 'Layer 2'},
    (3, 0): {'face': '#2ECC71', 'edge': '#27AE60', 'name': 'Layer 3'},
    (4, 0): {'face': '#9B59B6', 'edge': '#8E44AD', 'name': 'Layer 4'},
    (5, 0): {'face': '#E74C3C', 'edge': '#C0392B', 'name': 'Layer 5'},
}


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
