"""
Interactive slider-based viewer for seed_1337/turn4 heater structure.

Run locally (with gdsfactory + matplotlib installed):
    python3 interactive_viewer.py

Move the sliders to tweak geometry parameters and the preview will update.
Use Ctrl+C in the terminal to close the window if needed.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button, Slider

import gdsfactory as gf


@dataclass
class DeviceParams:
    # Outer Dimensions
    width_total: float = 5.5
    height_total: float = 3.0

    # Ring Geometry
    ring_width: float = 0.55

    # Inner Arm Geometry
    arm_y_offset: float = 0.62
    pad_width: float = 0.75
    pad_height: float = 0.52
    bridge_width: float = 0.25
    bridge_height: float = 0.30

    # Holes (Windows)
    hole_width: float = 0.45
    hole_height: float = 0.25


def build_component(p: DeviceParams) -> gf.Component:
    """Rebuild the device using the provided parameter set."""
    layer_main = (1, 0)

    # Derived parameters
    radius_outer = p.height_total / 2.0
    radius_center = radius_outer - p.ring_width / 2.0
    straight_length = p.width_total - p.height_total

    # Create Positive Geometry
    c_pos = gf.Component("Positive_Mask")

    # A. Racetrack Ring
    path = gf.Path()
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.arc(radius=radius_center, angle=180))

    xs_ring = gf.cross_section.cross_section(width=p.ring_width, layer=layer_main)
    ring = c_pos << gf.path.extrude(path, cross_section=xs_ring)
    ring.center = (0, 0)

    # B. Inner Arms Assembly
    pad_shape = gf.components.rectangle(size=(p.pad_width, p.pad_height), layer=layer_main, centered=True)
    bridge_shape = gf.components.rectangle(size=(p.bridge_width + 0.1, p.bridge_height), layer=layer_main, centered=True)

    def add_arm_pos(y_pos, mirror_y=False):
        x_pad_center_offset = p.pad_width / 2 + p.bridge_width / 2

        # Pads
        pl = c_pos << pad_shape
        pl.move((-x_pad_center_offset, y_pos))
        pr = c_pos << pad_shape
        pr.move((x_pad_center_offset, y_pos))

        # Bridge
        br = c_pos << bridge_shape
        br.move((0, y_pos))

        # Connections to Ring (Tapers)
        x_pad_edge = x_pad_center_offset + p.pad_width / 2
        y_pad_top = y_pos + p.pad_height / 2
        y_pad_bot = y_pos - p.pad_height / 2
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

    add_arm_pos(p.arm_y_offset, mirror_y=False)
    add_arm_pos(-p.arm_y_offset, mirror_y=True)

    # Create Negative Geometry (Holes)
    c_neg = gf.Component("Negative_Mask")
    hole_shape = gf.components.rectangle(size=(p.hole_width, p.hole_height), layer=layer_main, centered=True)

    def add_arm_holes(y_pos):
        x_pad_center_offset = p.pad_width / 2 + p.bridge_width / 2
        hl = c_neg << hole_shape
        hl.move((-x_pad_center_offset, y_pos))
        hr = c_neg << hole_shape
        hr.move((x_pad_center_offset, y_pos))

    add_arm_holes(p.arm_y_offset)
    add_arm_holes(-p.arm_y_offset)

    # Final Boolean Operation
    c_final = gf.boolean(A=c_pos, B=c_neg, operation="not", layer=layer_main)

    return c_final


def render_component(ax: plt.Axes, comp: gf.Component) -> None:
    """Render polygons on the provided axes for quick feedback."""
    ax.clear()

    polys_by_spec: Dict[Tuple[int, int], List[np.ndarray]] = comp.get_polygons(
        by_spec=True
    )
    for (_, _), polys in polys_by_spec.items():
        for pts in polys:
            patch = plt.Polygon(
                pts, facecolor="#5b8ff9", edgecolor="black", lw=0.6, alpha=0.7
            )
            ax.add_patch(patch)

    bbox = np.array(comp.bbox)
    (xmin, ymin), (xmax, ymax) = bbox
    span = max(xmax - xmin, ymax - ymin)
    margin = max(span * 0.15, 0.25)

    ax.set_xlim(xmin - margin, xmax + margin)
    ax.set_ylim(ymin - margin, ymax + margin)
    ax.set_aspect("equal")
    ax.set_xlabel("um")
    ax.set_ylabel("um")
    ax.set_title("seed_1337/turn4 heater structure preview")
    ax.figure.canvas.draw_idle()


def slider_definitions(defaults: DeviceParams):
    """Slider bounds for each tunable parameter."""
    return [
        ("width_total", 4.0, 7.0, defaults.width_total, 0.05),
        ("height_total", 2.0, 4.0, defaults.height_total, 0.05),
        ("ring_width", 0.3, 1.0, defaults.ring_width, 0.01),
        ("arm_y_offset", 0.3, 1.0, defaults.arm_y_offset, 0.02),
        ("pad_width", 0.4, 1.2, defaults.pad_width, 0.02),
        ("pad_height", 0.3, 0.8, defaults.pad_height, 0.02),
        ("bridge_width", 0.1, 0.5, defaults.bridge_width, 0.01),
        ("bridge_height", 0.15, 0.5, defaults.bridge_height, 0.01),
        ("hole_width", 0.2, 0.7, defaults.hole_width, 0.02),
        ("hole_height", 0.1, 0.4, defaults.hole_height, 0.02),
    ]


def main() -> None:
    defaults = DeviceParams()
    fig, ax = plt.subplots(figsize=(9, 7))
    plt.subplots_adjust(left=0.32, right=0.98, top=0.97, bottom=0.05)

    # Slider layout down the left side
    slider_height = 0.04
    slider_space = 0.01
    start_y = 0.95
    sliders: List[Tuple[str, Slider]] = []

    for idx, (name, vmin, vmax, vinit, step) in enumerate(
        slider_definitions(defaults)
    ):
        y = start_y - idx * (slider_height + slider_space)
        ax_slider = plt.axes([0.05, y, 0.22, slider_height])
        slider = Slider(
            ax=ax_slider,
            label=name,
            valmin=vmin,
            valmax=vmax,
            valinit=vinit,
            valstep=step,
        )
        sliders.append((name, slider))

    def current_params() -> DeviceParams:
        kwargs = {name: slider.val for name, slider in sliders}
        return DeviceParams(**kwargs)

    def handle_update(_):
        try:
            comp = build_component(current_params())
            render_component(ax, comp)
        except Exception as e:
            ax.set_title(f"Error: {e}")
            ax.figure.canvas.draw_idle()

    for _, slider in sliders:
        slider.on_changed(handle_update)

    # Reset button to restore defaults
    reset_ax = plt.axes([0.05, 0.01, 0.08, 0.035])
    reset_button = Button(reset_ax, "Reset", hovercolor="#e0e0e0")

    def reset(event):
        del event  # unused
        for _, slider in sliders:
            slider.reset()

    reset_button.on_clicked(reset)

    # Initial draw
    initial_component = build_component(defaults)
    render_component(ax, initial_component)

    plt.show()


if __name__ == "__main__":
    main()
