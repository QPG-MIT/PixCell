"""Primitives-only recreation of the compact folded corrugated waveguide."""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

layer = (1, 0)

# Named, live function-defining dimensions (um).
wg_width = 0.056
bus_width = 0.028
bus_length = 16.10
delta_length = 0.0
period = 0.160
tooth_width = 0.082
tooth_depth = 0.052
grating_length = 10.05
left_radius = 1.95
right_radius = 1.62
gap = 0.045
top_y = 0.662
upper_y = 0.423
lower_y = 0.277
bottom_y = 0.038
bus_y = 0.350


def add_path(component: gf.Component, points: list[tuple[float, float]], width: float) -> None:
    """Add a smooth centerline extruded at a constant core width."""
    path = gf.path.smooth(np.asarray(points, dtype=float), radius=0.03)
    component.add_ref(path.extrude(width=width, layer=layer))


@gf.cell
def folded_bragg() -> gf.Component:
    c = gf.Component()

    # Top input, right hairpin, upper interaction leg, and broad left return.
    add_path(
        c,
        [
            (2.20, top_y), (15.45, top_y),
            (16.85, 0.640), (17.30, 0.535), (17.18, 0.458),
            (16.20, upper_y), (2.48, upper_y),
            (0.52, 0.395), (0.18, 0.260), (0.55, 0.130),
            (2.35, bottom_y), (15.85, bottom_y),
        ],
        wg_width,
    )

    # The second corrugated leg, placed across the bus from the upper leg.
    add_path(
        c,
        [(3.45, lower_y), (15.50, lower_y), (16.70, 0.245), (17.40, 0.145), (17.92, 0.020)],
        wg_width,
    )

    # Straight through bus.
    # Two coincident centerlines are the reference and length-tuned paths.
    # At delta_length=0 they are geometrically identical; increasing it adds
    # only a real bus-width segment at the right-hand end.
    reference_path = gf.path.smooth(np.asarray([(1.88, bus_y), (1.88 + bus_length, bus_y)]), radius=0.03)
    tuned_path = gf.path.smooth(np.asarray([(1.88, bus_y), (1.88 + bus_length + delta_length, bus_y)]), radius=0.03)
    c.add_ref(reference_path.extrude(width=bus_width, layer=layer))
    c.add_ref(tuned_path.extrude(width=bus_width, layer=layer))

    # Corrugations are primitive rectangles attached to the interaction legs.
    n_teeth = int(grating_length / period)
    x0 = 5.15
    for i in range(n_teeth):
        x = x0 + i * period
        upper_tooth = gf.components.rectangle(size=(tooth_width, tooth_depth), layer=layer)
        ru = c.add_ref(upper_tooth)
        ru.dmove((x, upper_y - wg_width / 2 - tooth_depth + 0.004))
        lower_tooth = gf.components.rectangle(size=(tooth_width, tooth_depth), layer=layer)
        rl = c.add_ref(lower_tooth)
        rl.dmove((x, lower_y + wg_width / 2 - 0.004))

    # Primitive tapers reproduce the pointed launch and collection ends.
    top_taper = gf.components.taper(length=0.34, width1=0.004, width2=wg_width, layer=layer)
    rt = c.add_ref(top_taper)
    rt.drotate(180)
    rt.dmove((2.20, top_y))
    out_taper = gf.components.taper(length=0.38, width1=wg_width, width2=0.004, layer=layer)
    ro = c.add_ref(out_taper)
    ro.dmove((15.85, bottom_y))
    return c


if __name__ == "__main__":
    component = folded_bragg().copy()
    component.flatten()
    component.write_gds(Path(__file__).with_name("device.gds"))
    reference_length = gf.path.smooth(np.asarray([(1.88, bus_y), (1.88 + bus_length, bus_y)]), radius=0.03).length()
    tuned_length = gf.path.smooth(np.asarray([(1.88, bus_y), (1.88 + bus_length + delta_length, bus_y)]), radius=0.03).length()
    Path(__file__).with_name("lengths.json").write_text(json.dumps({
        "arms": {"reference_bus": reference_length, "tuned_bus": tuned_length},
        "delta_length_um": tuned_length - reference_length,
    }, indent=2))
