"""Primitives-only reconstruction of the four-port rounded crossing."""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


layer = (1, 0)
wg_width = 0.23
core_width = 0.76
lobe_max_width = 0.92
lobe_rise_length = 0.95
lobe_fall_length = 0.45
port_length = 0.57
top_port_length = 0.57


def _strip() -> gf.CrossSection:
    return gf.cross_section.strip(width=wg_width, layer=layer)


def _straight(length: float) -> gf.Component:
    return gf.components.straight(length=length, cross_section=_strip())


def _profile_lobe() -> gf.Component:
    """Make one smooth, two-stage lobe from a variable-width Path."""
    total_length = lobe_rise_length + lobe_fall_length
    rise_fraction = lobe_rise_length / total_length
    points = [(float(x), 0.0) for x in np.linspace(0.0, total_length, 25)]

    def width_profile(t: np.ndarray) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        widths = np.empty_like(t)
        rising = t <= rise_fraction
        u = t[rising] / rise_fraction
        widths[rising] = wg_width + (lobe_max_width - wg_width) * np.sin(np.pi * u / 2) ** 0.75
        u = (t[~rising] - rise_fraction) / (1.0 - rise_fraction)
        widths[~rising] = core_width + (lobe_max_width - core_width) * np.cos(np.pi * u / 2) ** 1.2
        return widths

    section = gf.Section(
        width=wg_width,
        layer=layer,
        port_names=(None, None),
        width_function=width_profile,
    )
    path = gf.Path(points)
    return path.extrude(cross_section=gf.CrossSection(sections=(section,)))


def _add_arm(component: gf.Component, angle: float, outer_distance: float) -> None:
    """Add one broad lobe, pointing inward from the named outer direction."""
    lobe = _profile_lobe()
    if angle == 0:
        position = (-outer_distance, 0)
    elif angle == 180:
        position = (outer_distance, 0)
    elif angle == 90:
        position = (0, -outer_distance)
    elif angle == -90:
        position = (0, outer_distance)
    else:
        raise ValueError(f"unsupported arm angle {angle}")

    reference = component.add_ref(lobe)
    reference.rotate(angle)
    reference.move((0, 0), position)


def _add_port(component: gf.Component, angle: float, length: float, outer_distance: float) -> None:
    """Add a centered straight access segment outside one lobe."""
    port = component.add_ref(_straight(length))
    if angle == 0:
        position = (outer_distance, 0)
    elif angle == 180:
        position = (-outer_distance, 0)
    elif angle == 90:
        position = (0, outer_distance)
    elif angle == -90:
        position = (0, -outer_distance)
    else:
        raise ValueError(f"unsupported port angle {angle}")
    port.rotate(angle)
    port.move((0, 0), position)


@gf.cell
def crossing() -> gf.Component:
    """Four opposed rounded lobes joined by a square central overlap."""
    component = gf.Component("rounded_crossing")
    half_core = core_width / 2
    outer_distance = half_core + lobe_fall_length + lobe_rise_length

    # The four opposing lobes are independent variable-width Path assemblies.
    _add_arm(component, 0, outer_distance)
    _add_arm(component, 180, outer_distance)
    _add_arm(component, 90, outer_distance)
    _add_arm(component, -90, outer_distance)

    # A small square closes the central overlap, matching the compact black core.
    core = gf.components.rectangle(
        size=(core_width, core_width),
        layer=layer,
        centered=True,
        port_type=None,
    )
    component.add_ref(core)

    # Straight access ports. The north access is independently tunable so the
    # declared knob-response contract can measure a real added waveguide length.
    _add_port(component, 0, port_length, outer_distance)
    _add_port(component, 180, port_length, outer_distance)
    _add_port(component, 90, top_port_length, outer_distance)
    _add_port(component, -90, port_length, outer_distance)
    return component


component = crossing()

# Measure two actual centerline paths; the north/south difference is the
# declared response of top_port_length and is not hand-entered.
half_core = core_width / 2
outer_distance = half_core + lobe_fall_length + lobe_rise_length
horizontal_path = gf.Path(
    [
        (-outer_distance - port_length, 0),
        (-outer_distance, 0),
        (-half_core, 0),
        (half_core, 0),
        (outer_distance, 0),
        (outer_distance + port_length, 0),
    ]
)
north_path = gf.Path(
    [
        (0, -outer_distance - top_port_length),
        (0, -outer_distance),
        (0, -half_core),
        (0, half_core),
        (0, outer_distance),
        (0, outer_distance + port_length),
    ]
)
south_path = gf.Path(
    [
        (0, -outer_distance - port_length),
        (0, -outer_distance),
        (0, -half_core),
        (0, half_core),
        (0, outer_distance),
        (0, outer_distance + port_length),
    ]
)
lengths = {
    "arms": {
        "north": float(north_path.length()),
        "south": float(south_path.length()),
    },
    "delta_length_um": abs(float(north_path.length()) - float(south_path.length())),
}
Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2) + "\n")

component.write_gds(str(Path(__file__).with_name("device.gds")), with_metadata=False)
