"""
Interactive GDSFactory Component Explorer - seed_1337/turn4

Run with: streamlit run interactive_explorer.py
"""

import streamlit as st
import gdsfactory as gf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.lines import Line2D
import io
import uuid
import json
import tempfile
import os
import numpy as np

# Target footprint from calibration
TARGET_FOOTPRINT = {
    "width_um": 5.5,   # horizontal
    "height_um": 3.0   # vertical
}

st.set_page_config(layout="wide", page_title="Seed 1337 Turn 4 Explorer")

st.title("Seed 1337 Turn 4 - Heater Structure Explorer")
st.markdown("**Best result: IoU=0.561** - Adjust parameters in the sidebar to explore variations.")

# =============================================================================
# SIDEBAR: Parameter Sliders
# =============================================================================

st.sidebar.header("Outer Dimensions")
width_total = st.sidebar.slider(
    "Total Width",
    min_value=4.0, max_value=7.0, value=5.5, step=0.05,
    help="Total width of the device"
)
height_total = st.sidebar.slider(
    "Total Height",
    min_value=2.0, max_value=4.0, value=3.0, step=0.05,
    help="Total height of the device"
)

st.sidebar.header("Ring Parameters")
ring_width = st.sidebar.slider(
    "Ring Width",
    min_value=0.3, max_value=1.0, value=0.55, step=0.01,
    help="Width of the outer racetrack ring"
)

st.sidebar.header("Inner Arm Parameters")
arm_y_offset = st.sidebar.slider(
    "Arm Y Offset",
    min_value=0.3, max_value=1.0, value=0.62, step=0.02,
    help="Vertical offset of arms from center"
)
pad_width = st.sidebar.slider(
    "Pad Width",
    min_value=0.4, max_value=1.2, value=0.75, step=0.02,
    help="Width of internal pads"
)
pad_height = st.sidebar.slider(
    "Pad Height",
    min_value=0.3, max_value=0.8, value=0.52, step=0.02,
    help="Height of internal pads"
)
bridge_width = st.sidebar.slider(
    "Bridge Width",
    min_value=0.1, max_value=0.5, value=0.25, step=0.01,
    help="Width of bridge connecting pads"
)
bridge_height = st.sidebar.slider(
    "Bridge Height",
    min_value=0.15, max_value=0.5, value=0.30, step=0.01,
    help="Height of bridge connecting pads"
)

st.sidebar.header("Hole Parameters")
hole_width = st.sidebar.slider(
    "Hole Width",
    min_value=0.2, max_value=0.7, value=0.45, step=0.02,
    help="Width of holes in pads"
)
hole_height = st.sidebar.slider(
    "Hole Height",
    min_value=0.1, max_value=0.4, value=0.25, step=0.02,
    help="Height of holes in pads"
)

st.sidebar.header("Visualization")
show_annotations = st.sidebar.checkbox(
    "Show annotations",
    value=True,
    help="Show labels for key features"
)

# =============================================================================
# COMPONENT GENERATION
# =============================================================================

def create_component(
    width_total, height_total, ring_width,
    arm_y_offset, pad_width, pad_height,
    bridge_width, bridge_height,
    hole_width, hole_height
):
    """Generate the parametric component with given parameters."""

    uid = str(uuid.uuid4())[:8]
    layer_main = (1, 0)

    # Derived parameters
    radius_outer = height_total / 2.0
    radius_center = radius_outer - ring_width / 2.0
    straight_length = width_total - height_total

    # Create Positive Geometry
    c_pos = gf.Component(f"Positive_{uid}")

    # A. Racetrack Ring
    path = gf.Path()
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))

    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_main)
    ring = c_pos << gf.path.extrude(path, cross_section=xs_ring)
    ring.center = (0, 0)

    # B. Inner Arms Assembly
    pad_shape = gf.components.rectangle(size=(pad_width, pad_height), layer=layer_main, centered=True)
    bridge_shape = gf.components.rectangle(size=(bridge_width + 0.1, bridge_height), layer=layer_main, centered=True)

    def add_arm_pos(y_pos, mirror_y=False):
        x_pad_center_offset = pad_width / 2 + bridge_width / 2

        # Pads
        pl = c_pos << pad_shape
        pl.move((-x_pad_center_offset, y_pos))
        pr = c_pos << pad_shape
        pr.move((x_pad_center_offset, y_pos))

        # Bridge
        br = c_pos << bridge_shape
        br.move((0, y_pos))

        # Connections to Ring (Tapers)
        x_pad_edge = x_pad_center_offset + pad_width / 2
        y_pad_top = y_pos + pad_height / 2
        y_pad_bot = y_pos - pad_height / 2
        x_end = 2.05

        if not mirror_y:
            pts_right = [
                (x_pad_edge, y_pad_top),
                (x_pad_edge, y_pad_bot),
                (x_end, -0.05),
                (x_end, y_pad_top)
            ]
        else:
            pts_right = [
                (x_pad_edge, y_pad_bot),
                (x_pad_edge, y_pad_top),
                (x_end, y_pad_bot),
                (x_end, 0.05)
            ]

        c_pos.add_polygon(pts_right, layer=layer_main)
        pts_left = [(-x, y) for x, y in pts_right]
        c_pos.add_polygon(pts_left, layer=layer_main)

    add_arm_pos(arm_y_offset, mirror_y=False)
    add_arm_pos(-arm_y_offset, mirror_y=True)

    # Create Negative Geometry (Holes)
    c_neg = gf.Component(f"Negative_{uid}")
    hole_shape = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_main, centered=True)

    def add_arm_holes(y_pos):
        x_pad_center_offset = pad_width / 2 + bridge_width / 2
        hl = c_neg << hole_shape
        hl.move((-x_pad_center_offset, y_pos))
        hr = c_neg << hole_shape
        hr.move((x_pad_center_offset, y_pos))

    add_arm_holes(arm_y_offset)
    add_arm_holes(-arm_y_offset)

    # Final Boolean Operation
    c_final = gf.boolean(A=c_pos, B=c_neg, operation="not", layer=layer_main)

    return c_final


# =============================================================================
# RENDER & DISPLAY
# =============================================================================

try:
    device = create_component(
        width_total, height_total, ring_width,
        arm_y_offset, pad_width, pad_height,
        bridge_width, bridge_height,
        hole_width, hole_height
    )

    # Get device bounding box
    bbox = device.bbox()
    try:
        gds_width = bbox[1][0] - bbox[0][0]
        gds_height = bbox[1][1] - bbox[0][1]
        gds_cx = (bbox[0][0] + bbox[1][0]) / 2
        gds_cy = (bbox[0][1] + bbox[1][1]) / 2
    except TypeError:
        gds_width = bbox.right - bbox.left
        gds_height = bbox.top - bbox.bottom
        gds_cx = (bbox.left + bbox.right) / 2
        gds_cy = (bbox.bottom + bbox.top) / 2
        bbox = [[bbox.left, bbox.bottom], [bbox.right, bbox.top]]

    # Target footprint
    target_w = TARGET_FOOTPRINT["width_um"]
    target_h = TARGET_FOOTPRINT["height_um"]

    # Create two columns
    col1, col2 = st.columns([3, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(12, 8))

        polygons_plotted = False
        hole_polygons = []

        default_color = {'face': '#2E86AB', 'edge': '#1B4965', 'name': 'Device'}

        try:
            polys = device.get_polygons()
            if isinstance(polys, dict):
                for layer, poly_list in polys.items():
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

                            try:
                                num_holes = poly.holes()
                                for hole_idx in range(num_holes):
                                    hole_pts = []
                                    for pt in poly.each_point_hole(hole_idx):
                                        hole_pts.append((pt.x / 1000, pt.y / 1000))

                                    if hole_pts:
                                        for i, pt in enumerate(hole_pts):
                                            vertices.append(pt)
                                            codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                                        vertices.append(hole_pts[0])
                                        codes.append(Path.CLOSEPOLY)

                                        hole_arr = np.array(hole_pts + [hole_pts[0]])
                                        ax.plot(hole_arr[:, 0], hole_arr[:, 1],
                                               color='#FF6B6B', linewidth=2.5, linestyle='-',
                                               zorder=10)
                                        hole_polygons.append(hole_arr)
                            except Exception:
                                pass

                            path = Path(vertices, codes)
                            patch = PathPatch(path, facecolor=default_color['face'],
                                            edgecolor=default_color['edge'],
                                            linewidth=1.5, alpha=0.9)
                            ax.add_patch(patch)
                            polygons_plotted = True

        except Exception as e:
            st.sidebar.warning(f"Polygon extraction: {e}")

        if not polygons_plotted:
            ax.add_patch(mpatches.Rectangle(
                (bbox[0][0], bbox[0][1]), gds_width, gds_height,
                linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.5,
                label='GDS bounds (polygons unavailable)'
            ))

        # Draw target footprint
        target_rect = mpatches.Rectangle(
            (gds_cx - target_w/2, gds_cy - target_h/2),
            target_w, target_h,
            linewidth=3, edgecolor='green', facecolor='none',
            linestyle='--', label=f'Target: {target_w}x{target_h} um'
        )
        ax.add_patch(target_rect)

        # Set axis limits
        pad = 0.5
        ax.set_xlim(min(bbox[0][0], gds_cx - target_w/2) - pad,
                   max(bbox[1][0], gds_cx + target_w/2) + pad)
        ax.set_ylim(min(bbox[0][1], gds_cy - target_h/2) - pad,
                   max(bbox[1][1], gds_cy + target_h/2) + pad)

        # Legend
        legend_elements = [
            mpatches.Patch(facecolor='#2E86AB', edgecolor='#1B4965', label='Device geometry'),
        ]
        if hole_polygons:
            legend_elements.append(mpatches.Patch(facecolor='white', edgecolor='#FF6B6B',
                          linewidth=2, label='Holes (cutouts)'))
        legend_elements.append(Line2D([0], [0], color='green', linewidth=3, linestyle='--',
                  label=f'Target: {target_w}x{target_h} um'))

        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        ax.set_title(f"GDS: {gds_width:.2f} x {gds_height:.2f} um | Target: {target_w} x {target_h} um", fontsize=12)
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

        # Annotations
        if show_annotations:
            x_pad_center_offset = pad_width / 2 + bridge_width / 2

            ax.annotate(f'Hole: {hole_width:.2f}x{hole_height:.2f}',
                       xy=(x_pad_center_offset, arm_y_offset),
                       xytext=(x_pad_center_offset + 0.8, arm_y_offset + 0.5),
                       fontsize=9, color='#FF6B6B', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='#FF6B6B', lw=1.5))

            ax.annotate(f'Ring: {ring_width:.2f} wide',
                       xy=(width_total/2 - 0.3, 0),
                       xytext=(width_total/2 + 0.3, 0.5),
                       fontsize=9, color='#1B4965', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='#1B4965', lw=1.5))

            ax.annotate(f'Arm Y: {arm_y_offset:.2f}',
                       xy=(0, arm_y_offset),
                       xytext=(-1.5, arm_y_offset + 0.3),
                       fontsize=9, color='#E76F51', fontweight='bold',
                       arrowprops=dict(arrowstyle='->', color='#E76F51', lw=1.5))

        st.pyplot(fig)
        plt.close(fig)

    with col2:
        st.subheader("Size Comparison")

        width_diff = gds_width - target_w
        height_diff = gds_height - target_h

        st.metric("GDS Width", f"{gds_width:.3f} um", f"{width_diff:+.3f}")
        st.metric("GDS Height", f"{gds_height:.3f} um", f"{height_diff:+.3f}")

        st.divider()
        st.metric("Target Width", f"{target_w:.1f} um")
        st.metric("Target Height", f"{target_h:.1f} um")

        st.divider()
        width_ok = abs(width_diff) < 0.1
        height_ok = abs(height_diff) < 0.1

        if width_ok and height_ok:
            st.success("Size matches target!")
        else:
            if not width_ok:
                st.warning(f"Width off by {width_diff:+.2f} um")
            if not height_ok:
                st.warning(f"Height off by {height_diff:+.2f} um")

        st.divider()

        st.subheader("Current Values")
        st.json({
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
        })

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
                label="Download GDS",
                data=gds_bytes,
                file_name="seed1337_turn4_modified.gds",
                mime="application/octet-stream"
            )
        except Exception as e:
            st.warning(f"GDS export unavailable: {e}")

except Exception as e:
    st.error(f"Error generating component: {str(e)}")
    st.info("Try adjusting parameters to valid ranges. Some parameter combinations may cause geometry conflicts.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
**Seed 1337 Turn 4 - Best Result (IoU=0.561)**

This is the best performing iteration from the fresh Phase 1 + Phase 2 run with absolute scaling.

**Tips:**
- Adjust sliders in the sidebar to modify the component
- The preview updates automatically as you change values
- Download the GDS file when you find a configuration you like
""")
