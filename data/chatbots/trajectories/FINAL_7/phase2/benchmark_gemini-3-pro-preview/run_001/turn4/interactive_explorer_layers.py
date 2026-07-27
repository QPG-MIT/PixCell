"""
Interactive GDSFactory Component Explorer with Layer Assignment

Run with: streamlit run interactive_explorer_layers.py
"""

import streamlit as st
import gdsfactory as gf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.lines import Line2D
import uuid
import tempfile
import os
import numpy as np

# Target footprint from calibration
TARGET_FOOTPRINT = {
    "width_um": 5.5,
    "height_um": 3.0
}

st.set_page_config(layout="wide", page_title="Layer Assignment Explorer")

st.title("Seed 1337 Turn 4 - Layer Assignment Explorer")
st.markdown("Assign different geometric elements to different GDS layers for multi-layer fabrication.")

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if 'layers' not in st.session_state:
    st.session_state.layers = {
        "Layer 1": {"layer": 1, "datatype": 0, "color": "#2E86AB"},
        "Layer 2": {"layer": 2, "datatype": 0, "color": "#F4A261"},
        "Layer 3": {"layer": 3, "datatype": 0, "color": "#E76F51"},
    }

if 'assignments' not in st.session_state:
    st.session_state.assignments = {
        "Ring": "Layer 1",
        "Pads": "Layer 1",
        "Bridges": "Layer 1",
        "Tapers": "Layer 1",
        "Holes": "Layer 1",
    }

# =============================================================================
# SIDEBAR: Layer Definition & Assignment
# =============================================================================

st.sidebar.header("Layer Definitions")

# Add new layer
with st.sidebar.expander("Add New Layer", expanded=False):
    new_layer_name = st.text_input("Layer Name", value="Layer 4")
    col1, col2 = st.columns(2)
    with col1:
        new_layer_num = st.number_input("Layer #", min_value=1, max_value=255, value=4)
    with col2:
        new_datatype = st.number_input("Datatype", min_value=0, max_value=255, value=0)
    new_color = st.color_picker("Color", value="#9B59B6")

    if st.button("Add Layer"):
        if new_layer_name not in st.session_state.layers:
            st.session_state.layers[new_layer_name] = {
                "layer": new_layer_num,
                "datatype": new_datatype,
                "color": new_color
            }
            st.rerun()
        else:
            st.warning("Layer name already exists!")

# Display existing layers
st.sidebar.markdown("---")
st.sidebar.subheader("Defined Layers")

layers_to_remove = []
for layer_name, layer_info in st.session_state.layers.items():
    col1, col2, col3 = st.sidebar.columns([2, 1, 1])
    with col1:
        st.markdown(f"**{layer_name}**")
        st.caption(f"({layer_info['layer']}, {layer_info['datatype']})")
    with col2:
        st.color_picker(
            "c",
            value=layer_info['color'],
            key=f"color_{layer_name}",
            label_visibility="collapsed",
            on_change=lambda ln=layer_name: st.session_state.layers[ln].update(
                {"color": st.session_state[f"color_{ln}"]}
            )
        )
    with col3:
        if len(st.session_state.layers) > 1:
            if st.button("X", key=f"del_{layer_name}"):
                layers_to_remove.append(layer_name)

for layer_name in layers_to_remove:
    del st.session_state.layers[layer_name]
    # Reassign any components using this layer to the first available layer
    first_layer = list(st.session_state.layers.keys())[0]
    for comp, assigned_layer in st.session_state.assignments.items():
        if assigned_layer == layer_name:
            st.session_state.assignments[comp] = first_layer
    st.rerun()

# Layer assignments
st.sidebar.markdown("---")
st.sidebar.header("Layer Assignments")
st.sidebar.caption("Assign each component to a layer")

component_descriptions = {
    "Ring": "Outer racetrack ring",
    "Pads": "Internal rectangular pads",
    "Bridges": "Thin bridges connecting pads",
    "Tapers": "Tapered connections to ring",
    "Holes": "Cutout windows in pads",
}

layer_names = list(st.session_state.layers.keys())

for comp_name, description in component_descriptions.items():
    current_assignment = st.session_state.assignments.get(comp_name, layer_names[0])
    if current_assignment not in layer_names:
        current_assignment = layer_names[0]
        st.session_state.assignments[comp_name] = current_assignment

    new_assignment = st.sidebar.selectbox(
        f"{comp_name}",
        options=layer_names,
        index=layer_names.index(current_assignment),
        key=f"assign_{comp_name}",
        help=description
    )
    st.session_state.assignments[comp_name] = new_assignment

# =============================================================================
# SIDEBAR: Geometry Parameters
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.header("Geometry Parameters")

with st.sidebar.expander("Outer Dimensions", expanded=True):
    width_total = st.slider("Total Width", 4.0, 7.0, 5.5, 0.05)
    height_total = st.slider("Total Height", 2.0, 4.0, 3.0, 0.05)
    ring_width = st.slider("Ring Width", 0.3, 1.0, 0.55, 0.01)

with st.sidebar.expander("Inner Arms", expanded=True):
    arm_y_offset = st.slider("Arm Y Offset", 0.3, 1.0, 0.62, 0.02)
    pad_width = st.slider("Pad Width", 0.4, 1.2, 0.75, 0.02)
    pad_height = st.slider("Pad Height", 0.3, 0.8, 0.52, 0.02)
    bridge_width = st.slider("Bridge Width", 0.1, 0.5, 0.25, 0.01)
    bridge_height = st.slider("Bridge Height", 0.15, 0.5, 0.30, 0.01)

with st.sidebar.expander("Holes", expanded=True):
    hole_width = st.slider("Hole Width", 0.2, 0.7, 0.45, 0.02)
    hole_height = st.slider("Hole Height", 0.1, 0.4, 0.25, 0.02)

# =============================================================================
# COMPONENT GENERATION WITH LAYER ASSIGNMENT
# =============================================================================

def create_component_with_layers(
    width_total, height_total, ring_width,
    arm_y_offset, pad_width, pad_height,
    bridge_width, bridge_height,
    hole_width, hole_height,
    layers_def, assignments
):
    """Generate the component with layer assignments."""

    uid = str(uuid.uuid4())[:8]

    # Get layer tuples from assignments
    def get_layer(component_name):
        layer_name = assignments.get(component_name, list(layers_def.keys())[0])
        layer_info = layers_def.get(layer_name, {"layer": 1, "datatype": 0})
        return (layer_info["layer"], layer_info["datatype"])

    layer_ring = get_layer("Ring")
    layer_pads = get_layer("Pads")
    layer_bridges = get_layer("Bridges")
    layer_tapers = get_layer("Tapers")
    layer_holes = get_layer("Holes")

    # Derived parameters
    radius_outer = height_total / 2.0
    radius_center = radius_outer - ring_width / 2.0
    straight_length = width_total - height_total

    # Main component
    c = gf.Component(f"Device_{uid}")

    # A. Racetrack Ring
    path = gf.Path()
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))

    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_ring)
    ring = c << gf.path.extrude(path, cross_section=xs_ring)
    ring.center = (0, 0)

    # B. Pads
    pad_shape = gf.components.rectangle(size=(pad_width, pad_height), layer=layer_pads, centered=True)
    x_pad_center_offset = pad_width / 2 + bridge_width / 2

    for y_pos in [arm_y_offset, -arm_y_offset]:
        pl = c << pad_shape
        pl.move((-x_pad_center_offset, y_pos))
        pr = c << pad_shape
        pr.move((x_pad_center_offset, y_pos))

    # C. Bridges
    bridge_shape = gf.components.rectangle(size=(bridge_width + 0.1, bridge_height), layer=layer_bridges, centered=True)
    for y_pos in [arm_y_offset, -arm_y_offset]:
        br = c << bridge_shape
        br.move((0, y_pos))

    # D. Tapers
    x_pad_edge = x_pad_center_offset + pad_width / 2
    x_end = 2.05

    # Top arm tapers
    y_pos = arm_y_offset
    y_pad_top = y_pos + pad_height / 2
    y_pad_bot = y_pos - pad_height / 2

    pts_right_top = [
        (x_pad_edge, y_pad_top),
        (x_pad_edge, y_pad_bot),
        (x_end, -0.05),
        (x_end, y_pad_top)
    ]
    c.add_polygon(pts_right_top, layer=layer_tapers)
    pts_left_top = [(-x, y) for x, y in pts_right_top]
    c.add_polygon(pts_left_top, layer=layer_tapers)

    # Bottom arm tapers
    y_pos = -arm_y_offset
    y_pad_top = y_pos + pad_height / 2
    y_pad_bot = y_pos - pad_height / 2

    pts_right_bot = [
        (x_pad_edge, y_pad_bot),
        (x_pad_edge, y_pad_top),
        (x_end, y_pad_bot),
        (x_end, 0.05)
    ]
    c.add_polygon(pts_right_bot, layer=layer_tapers)
    pts_left_bot = [(-x, y) for x, y in pts_right_bot]
    c.add_polygon(pts_left_bot, layer=layer_tapers)

    # E. Holes (as actual geometry, not boolean)
    # For multi-layer, we add holes as separate layer geometry
    # If holes are on same layer as pads, we'd need boolean - but for visualization we show them
    hole_shape = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_holes, centered=True)

    for y_pos in [arm_y_offset, -arm_y_offset]:
        hl = c << hole_shape
        hl.move((-x_pad_center_offset, y_pos))
        hr = c << hole_shape
        hr.move((x_pad_center_offset, y_pos))

    return c


# =============================================================================
# RENDER & DISPLAY
# =============================================================================

try:
    device = create_component_with_layers(
        width_total, height_total, ring_width,
        arm_y_offset, pad_width, pad_height,
        bridge_width, bridge_height,
        hole_width, hole_height,
        st.session_state.layers,
        st.session_state.assignments
    )

    # Get device bounding box - handle different gdsfactory versions
    bbox_raw = device.bbox
    if callable(bbox_raw):
        bbox_raw = bbox_raw()

    try:
        # Try array-like access first (numpy array or list)
        if hasattr(bbox_raw, '__getitem__'):
            gds_width = float(bbox_raw[1][0] - bbox_raw[0][0])
            gds_height = float(bbox_raw[1][1] - bbox_raw[0][1])
            gds_cx = float((bbox_raw[0][0] + bbox_raw[1][0]) / 2)
            gds_cy = float((bbox_raw[0][1] + bbox_raw[1][1]) / 2)
            bbox = [[float(bbox_raw[0][0]), float(bbox_raw[0][1])],
                    [float(bbox_raw[1][0]), float(bbox_raw[1][1])]]
        else:
            raise TypeError("Not indexable")
    except (TypeError, IndexError):
        # Try DBox-style access
        gds_width = float(bbox_raw.right - bbox_raw.left)
        gds_height = float(bbox_raw.top - bbox_raw.bottom)
        gds_cx = float((bbox_raw.left + bbox_raw.right) / 2)
        gds_cy = float((bbox_raw.bottom + bbox_raw.top) / 2)
        bbox = [[float(bbox_raw.left), float(bbox_raw.bottom)],
                [float(bbox_raw.right), float(bbox_raw.top)]]

    target_w = TARGET_FOOTPRINT["width_um"]
    target_h = TARGET_FOOTPRINT["height_um"]

    # Create columns
    col1, col2 = st.columns([3, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(12, 8))

        # Build color map from layer definitions
        layer_colors = {}
        for layer_name, layer_info in st.session_state.layers.items():
            layer_tuple = (layer_info["layer"], layer_info["datatype"])
            layer_colors[layer_tuple] = {
                'face': layer_info['color'],
                'edge': layer_info['color'],
                'name': layer_name
            }

        polygons_plotted = False
        plotted_layers = {}  # layer_tuple -> layer_name

        try:
            polys = device.get_polygons()
            if isinstance(polys, dict):
                for layer_key, poly_list in polys.items():
                    # Normalize layer key to tuple
                    if isinstance(layer_key, tuple):
                        layer_tuple = layer_key
                    elif isinstance(layer_key, int):
                        layer_tuple = (layer_key, 0)
                    else:
                        layer_tuple = (1, 0)  # fallback

                    colors = layer_colors.get(layer_tuple, {'face': '#888888', 'edge': '#666666', 'name': f'Layer {layer_tuple}'})
                    plotted_layers[layer_tuple] = colors['name']

                    for poly in poly_list:
                        vertices = []
                        codes = []

                        hull_pts = []
                        for pt in poly.each_point_hull():
                            hull_pts.append((pt.x / 1000, pt.y / 1000))

                        if hull_pts:
                            for i, pt in enumerate(hull_pts):
                                vertices.append(pt)
                                codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                            vertices.append(hull_pts[0])
                            codes.append(Path.CLOSEPOLY)

                            path = Path(vertices, codes)
                            patch = PathPatch(path, facecolor=colors['face'],
                                            edgecolor=colors['edge'],
                                            linewidth=1.5, alpha=0.7)
                            ax.add_patch(patch)
                            polygons_plotted = True

        except Exception as e:
            st.sidebar.warning(f"Polygon extraction: {e}")

        if not polygons_plotted:
            ax.add_patch(mpatches.Rectangle(
                (bbox[0][0], bbox[0][1]), gds_width, gds_height,
                linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.5
            ))

        # Draw target footprint
        target_rect = mpatches.Rectangle(
            (gds_cx - target_w/2, gds_cy - target_h/2),
            target_w, target_h,
            linewidth=3, edgecolor='green', facecolor='none',
            linestyle='--'
        )
        ax.add_patch(target_rect)

        # Set axis limits
        pad = 0.5
        ax.set_xlim(min(bbox[0][0], gds_cx - target_w/2) - pad,
                   max(bbox[1][0], gds_cx + target_w/2) + pad)
        ax.set_ylim(min(bbox[0][1], gds_cy - target_h/2) - pad,
                   max(bbox[1][1], gds_cy + target_h/2) + pad)

        # Legend with layer colors
        legend_elements = []
        for layer_tuple, layer_name in sorted(plotted_layers.items()):
            colors = layer_colors.get(layer_tuple, {'face': '#888888', 'name': f'Layer {layer_tuple}'})
            legend_elements.append(
                mpatches.Patch(facecolor=colors['face'], edgecolor=colors['face'],
                              alpha=0.7, label=f"{layer_name} ({layer_tuple[0]},{layer_tuple[1]})")
            )
        legend_elements.append(Line2D([0], [0], color='green', linewidth=3, linestyle='--',
                  label=f'Target: {target_w}x{target_h} um'))

        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        ax.set_title(f"Multi-Layer View | GDS: {gds_width:.2f} x {gds_height:.2f} um", fontsize=12)
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

        st.pyplot(fig)
        plt.close(fig)

    with col2:
        st.subheader("Layer Summary")

        # Show which components are on which layers
        for layer_name, layer_info in st.session_state.layers.items():
            components_on_layer = [
                comp for comp, assigned in st.session_state.assignments.items()
                if assigned == layer_name
            ]
            if components_on_layer:
                st.markdown(f"**{layer_name}** ({layer_info['layer']},{layer_info['datatype']})")
                for comp in components_on_layer:
                    st.caption(f"  - {comp}")

        st.divider()

        st.subheader("Size Info")
        st.metric("GDS Width", f"{gds_width:.3f} um")
        st.metric("GDS Height", f"{gds_height:.3f} um")

        st.divider()

        st.subheader("Export")

        try:
            with tempfile.NamedTemporaryFile(suffix='.gds', delete=False) as tmp:
                tmp_path = tmp.name
            device.write_gds(tmp_path)
            with open(tmp_path, 'rb') as f:
                gds_bytes = f.read()
            os.unlink(tmp_path)

            st.download_button(
                label="Download Multi-Layer GDS",
                data=gds_bytes,
                file_name="seed1337_multilayer.gds",
                mime="application/octet-stream"
            )
        except Exception as e:
            st.warning(f"GDS export unavailable: {e}")

        # Export layer map as JSON
        layer_map = {
            "layers": st.session_state.layers,
            "assignments": st.session_state.assignments,
            "parameters": {
                "width_total": width_total,
                "height_total": height_total,
                "ring_width": ring_width,
                "arm_y_offset": arm_y_offset,
                "pad_width": pad_width,
                "pad_height": pad_height,
                "bridge_width": bridge_width,
                "bridge_height": bridge_height,
                "hole_width": hole_width,
                "hole_height": hole_height
            }
        }

        import json
        st.download_button(
            label="Download Layer Map (JSON)",
            data=json.dumps(layer_map, indent=2),
            file_name="layer_assignments.json",
            mime="application/json"
        )

except Exception as e:
    st.error(f"Error generating component: {str(e)}")
    st.info("Try adjusting parameters to valid ranges.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
**Layer Assignment Explorer**

This tool allows you to:
1. **Define layers** - Create custom GDS layers with layer number, datatype, and visualization color
2. **Assign components** - Map each geometric element (Ring, Pads, Bridges, Tapers, Holes) to a layer
3. **Export** - Download multi-layer GDS files for fabrication

**Component Types:**
- **Ring**: Outer racetrack structure
- **Pads**: Rectangular pads in the internal structure
- **Bridges**: Thin connections between pads
- **Tapers**: Triangular transitions connecting pads to ring
- **Holes**: Cutout windows (note: if on same layer as pads, boolean subtraction is applied)
""")
