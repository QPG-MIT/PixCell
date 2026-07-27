"""
3D GDS Viewer Module

Interactive 3D visualization of GDS components using Plotly.
Provides rotate, zoom, pan controls with layer visibility toggles.
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from scipy.spatial import Delaunay

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None

from .theme import get_layer_color, COLORS


def is_available() -> bool:
    """Check if Plotly is available."""
    return PLOTLY_AVAILABLE


def triangulate_polygon(vertices: List[Tuple[float, float]]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Triangulate a 2D polygon for 3D mesh rendering.

    Args:
        vertices: List of (x, y) vertex coordinates

    Returns:
        Tuple of (points array, triangles array)
    """
    points = np.array(vertices)

    if len(points) < 3:
        return points, np.array([])

    try:
        # Use Delaunay triangulation
        tri = Delaunay(points)
        return points, tri.simplices
    except Exception:
        # Fallback: fan triangulation from first vertex
        n = len(points)
        if n < 3:
            return points, np.array([])
        triangles = np.array([[0, i, i + 1] for i in range(1, n - 1)])
        return points, triangles


def create_extruded_mesh(
    vertices: List[Tuple[float, float]],
    z_min: float,
    z_max: float,
    color: str,
    name: str = "Layer",
    opacity: float = 0.9
) -> List[Any]:
    """
    Create 3D extruded mesh from 2D polygon.

    Args:
        vertices: List of (x, y) vertex coordinates
        z_min: Bottom Z coordinate
        z_max: Top Z coordinate
        color: Hex color string
        name: Layer name for legend
        opacity: Mesh opacity (0-1)

    Returns:
        List of Mesh3d objects (top, bottom, sides)
    """
    if not PLOTLY_AVAILABLE:
        return []

    if len(vertices) < 3:
        return []

    meshes = []
    points, triangles = triangulate_polygon(vertices)

    if len(triangles) == 0:
        return []

    n_points = len(points)

    # Top face
    x_top = points[:, 0]
    y_top = points[:, 1]
    z_top = np.full(n_points, z_max)

    meshes.append(go.Mesh3d(
        x=x_top, y=y_top, z=z_top,
        i=triangles[:, 0], j=triangles[:, 1], k=triangles[:, 2],
        color=color,
        opacity=opacity,
        name=name,
        showlegend=True,
        legendgroup=name,
        flatshading=True,
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2),
    ))

    # Bottom face
    z_bottom = np.full(n_points, z_min)

    meshes.append(go.Mesh3d(
        x=x_top, y=y_top, z=z_bottom,
        i=triangles[:, 0], j=triangles[:, 2], k=triangles[:, 1],  # Reverse winding
        color=color,
        opacity=opacity,
        name=name,
        showlegend=False,
        legendgroup=name,
        flatshading=True,
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2),
    ))

    # Side faces
    for i in range(n_points):
        j = (i + 1) % n_points

        # Two triangles per side quad
        x_side = [points[i, 0], points[j, 0], points[j, 0], points[i, 0]]
        y_side = [points[i, 1], points[j, 1], points[j, 1], points[i, 1]]
        z_side = [z_min, z_min, z_max, z_max]

        meshes.append(go.Mesh3d(
            x=x_side, y=y_side, z=z_side,
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=color,
            opacity=opacity,
            name=name,
            showlegend=False,
            legendgroup=name,
            flatshading=True,
            lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2),
        ))

    return meshes


def extract_polygons_from_component(
    component: Any,
    layers: Optional[List[Tuple[int, int]]] = None
) -> Dict[Tuple[int, int], List[List[Tuple[float, float]]]]:
    """
    Extract polygons from a GDSFactory component.

    Args:
        component: GDSFactory Component
        layers: Optional list of layers to include (all if None)

    Returns:
        Dict mapping layer tuple to list of polygon vertex lists
    """
    result = {}

    try:
        # Get all polygons from component
        polygons_dict = component.get_polygons(by_spec=True)

        for layer_spec, polys in polygons_dict.items():
            # Handle layer specification
            if isinstance(layer_spec, tuple):
                layer = layer_spec
            else:
                layer = (layer_spec, 0)

            # Filter by requested layers
            if layers is not None and layer not in layers:
                continue

            # Convert polygon arrays to vertex lists
            poly_list = []
            for poly in polys:
                if hasattr(poly, 'tolist'):
                    vertices = [(float(p[0]), float(p[1])) for p in poly.tolist()]
                else:
                    vertices = [(float(p[0]), float(p[1])) for p in poly]

                if len(vertices) >= 3:
                    poly_list.append(vertices)

            if poly_list:
                result[layer] = poly_list

    except Exception as e:
        # Fallback: try to get polygons without by_spec
        try:
            all_polys = component.get_polygons()
            if all_polys:
                result[(1, 0)] = [
                    [(float(p[0]), float(p[1])) for p in poly]
                    for poly in all_polys
                    if len(poly) >= 3
                ]
        except Exception:
            pass

    return result


def create_3d_figure(
    component: Any,
    layers: Optional[List[Tuple[int, int]]] = None,
    thickness_um: float = 0.22,
    layer_colors: Optional[Dict[Tuple[int, int], str]] = None,
    layer_opacities: Optional[Dict[Tuple[int, int], float]] = None,
    show_substrate: bool = True,
    title: str = "3D Device View"
) -> Any:
    """
    Create interactive 3D Plotly figure from GDS component.

    Args:
        component: GDSFactory Component
        layers: Layers to display (all if None)
        thickness_um: Extrusion height in micrometers
        layer_colors: Custom colors per layer
        layer_opacities: Custom opacity per layer (0-1)
        show_substrate: Show substrate plane below device
        title: Figure title

    Returns:
        Plotly Figure object
    """
    if not PLOTLY_AVAILABLE:
        raise RuntimeError("Plotly is not installed")

    # Extract polygons
    polygons_by_layer = extract_polygons_from_component(component, layers)

    if not polygons_by_layer:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No polygons found in component",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color=COLORS["text_muted"])
        )
        return fig

    # Collect all traces
    traces = []

    # Get bounding box for substrate
    all_x = []
    all_y = []

    for layer, polys in polygons_by_layer.items():
        # Get layer color
        if layer_colors and layer in layer_colors:
            color = layer_colors[layer]
        else:
            color = get_layer_color(layer)["face"]

        # Get layer opacity
        if layer_opacities and layer in layer_opacities:
            opacity = layer_opacities[layer]
        else:
            opacity = 0.85

        # Get layer name
        layer_name = get_layer_color(layer)["name"]

        # Create meshes for each polygon
        for poly_vertices in polys:
            meshes = create_extruded_mesh(
                poly_vertices,
                z_min=0,
                z_max=thickness_um,
                color=color,
                name=layer_name,
                opacity=opacity
            )
            traces.extend(meshes)

            # Track bounds
            for x, y in poly_vertices:
                all_x.append(x)
                all_y.append(y)

    # Add substrate plane
    if show_substrate and all_x and all_y:
        pad = 0.5
        x_min, x_max = min(all_x) - pad, max(all_x) + pad
        y_min, y_max = min(all_y) - pad, max(all_y) + pad

        substrate = go.Mesh3d(
            x=[x_min, x_max, x_max, x_min],
            y=[y_min, y_min, y_max, y_max],
            z=[-0.1, -0.1, -0.1, -0.1],
            i=[0, 0], j=[1, 2], k=[2, 3],
            color=COLORS["bg_hover"],
            opacity=0.5,
            name="Substrate",
            showlegend=True,
            flatshading=True,
        )
        traces.insert(0, substrate)

    # Create figure
    fig = go.Figure(data=traces)

    # Configure layout
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=COLORS["text"], size=16),
            x=0.5
        ),
        scene=dict(
            xaxis=dict(
                title="X (um)",
                backgroundcolor=COLORS["bg_dark"],
                gridcolor=COLORS["border"],
                showbackground=True,
                color=COLORS["text_muted"],
            ),
            yaxis=dict(
                title="Y (um)",
                backgroundcolor=COLORS["bg_dark"],
                gridcolor=COLORS["border"],
                showbackground=True,
                color=COLORS["text_muted"],
            ),
            zaxis=dict(
                title="Z (um)",
                backgroundcolor=COLORS["bg_dark"],
                gridcolor=COLORS["border"],
                showbackground=True,
                color=COLORS["text_muted"],
            ),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2),
                up=dict(x=0, y=0, z=1)
            ),
        ),
        paper_bgcolor=COLORS["bg_dark"],
        plot_bgcolor=COLORS["bg_dark"],
        legend=dict(
            bgcolor=COLORS["bg_card"],
            bordercolor=COLORS["border"],
            borderwidth=1,
            font=dict(color=COLORS["text"]),
            itemsizing='constant',
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return fig


def render_3d_viewer(
    st,
    component: Any,
    key: str = "viewer_3d",
    height: int = 500,
    default_thickness: float = 0.22
) -> None:
    """
    Render interactive 3D viewer with controls in Streamlit.

    Args:
        st: Streamlit module
        component: GDSFactory Component
        key: Unique key for Streamlit widgets
        height: Figure height in pixels
        default_thickness: Default extrusion thickness in um
    """
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly is not installed. Install with: pip install plotly")
        return

    if component is None:
        st.warning("No component to display")
        return

    # Get available layers
    polygons_by_layer = extract_polygons_from_component(component)
    available_layers = list(polygons_by_layer.keys())

    if not available_layers:
        st.warning("No polygons found in component")
        return

    # Initialize session state for this viewer
    state_key = f"{key}_state"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "visible_layers": {layer: True for layer in available_layers},
            "opacities": {layer: 0.85 for layer in available_layers},
            "thickness": default_thickness,
        }

    viewer_state = st.session_state[state_key]

    # Controls in expander
    with st.expander("Layer Controls", expanded=False):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("**Layer Visibility**")
            for layer in available_layers:
                layer_info = get_layer_color(layer)
                visible = st.checkbox(
                    f"{layer_info['name']} ({layer[0]}/{layer[1]})",
                    value=viewer_state["visible_layers"].get(layer, True),
                    key=f"{key}_vis_{layer}"
                )
                viewer_state["visible_layers"][layer] = visible

        with col2:
            st.markdown("**Thickness**")
            thickness = st.slider(
                "Thickness (um)",
                min_value=0.05,
                max_value=2.0,
                value=viewer_state["thickness"],
                step=0.01,
                key=f"{key}_thickness",
                label_visibility="collapsed"
            )
            viewer_state["thickness"] = thickness

    # Filter visible layers
    visible_layers = [
        layer for layer in available_layers
        if viewer_state["visible_layers"].get(layer, True)
    ]

    if not visible_layers:
        st.info("No layers selected. Enable at least one layer to view.")
        return

    # Create and display figure
    try:
        fig = create_3d_figure(
            component,
            layers=visible_layers,
            thickness_um=viewer_state["thickness"],
            layer_opacities=viewer_state["opacities"],
            show_substrate=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            height=height,
            key=f"{key}_chart"
        )

    except Exception as e:
        st.error(f"Error creating 3D view: {e}")


def render_view_toggle(st, component: Any, key: str = "view") -> None:
    """
    Render 2D/3D view toggle with both visualizations.

    Args:
        st: Streamlit module
        component: GDSFactory Component
        key: Unique key prefix
    """
    from . import visualization

    tab1, tab2 = st.tabs(["2D View", "3D View"])

    with tab1:
        try:
            fig = visualization.create_device_figure(component)
            st.pyplot(fig)
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception as e:
            st.error(f"Error creating 2D view: {e}")

    with tab2:
        render_3d_viewer(st, component, key=f"{key}_3d")
