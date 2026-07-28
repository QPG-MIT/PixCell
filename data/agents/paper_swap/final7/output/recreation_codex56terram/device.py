"""Primitives-only recreation of the supplied loop-loaded device."""
from pathlib import Path

import gdsfactory as gf
import numpy as np
import json

LAYER = (1, 0)

# Top-level parametric contract: all function-defining dimensions are live.
outer_radius_um = 1.30
outer_straight_um = 2.90
loop_width_um = 0.40
loading_body_width_um = 0.90
loading_body_height_um = 1.02
loading_offset_um = 1.34
slot_width_um = 0.33
slot_height_um = 0.54
slot_gap_um = 0.14
bridge_width_um = 0.14
feed_width_um = 0.42
feed_length_um = 0.72
# A zero-baseline optical-length trim. It is a real routed path when enabled
# and provides the standard parametric path-length contract for later retargeting.
delta_length = 0.0


def _rect(size: tuple[float, float], origin: tuple[float, float]) -> gf.Component:
    """A translated primitive rectangle, kept as a component for boolean use."""
    c = gf.Component()
    ref = c.add_ref(gf.components.rectangle(size=size, layer=LAYER))
    ref.dmove(origin)
    return c


@gf.cell
def loop_loaded_device() -> gf.Component:
    c = gf.Component()

    # A closed, smoothly rounded vertical racetrack centerline. Its extrema
    # plus half the track width follow the calibrated 3.0 x 5.5 um envelope.
    loop_points = np.array([
        (0.20, 1.30), (0.63, 0.55), (1.50, 0.20), (2.37, 0.55),
        (2.80, 1.30), (2.80, 4.20), (2.37, 4.95), (1.50, 5.30),
        (0.63, 4.95), (0.20, 4.20), (0.20, 1.30),
    ])
    loop = gf.path.smooth(loop_points, radius=0.30)
    c.add_ref(loop.extrude(width=loop_width_um, layer=LAYER))

    # Two symmetric loading bodies, each cut with two slots. Boolean is used
    # only on primitive rectangles; no raw polygon geometry is emitted.
    for y0 in (loading_offset_um, 5.50 - loading_offset_um - loading_body_height_um):
        body = _rect((loading_body_width_um, loading_body_height_um), (1.05, y0))
        slot_y = y0 + (loading_body_height_um - slot_height_um) / 2
        left_slot = _rect((slot_width_um, slot_height_um), (1.11, slot_y))
        right_slot = _rect((slot_width_um, slot_height_um), (1.11 + slot_width_um + slot_gap_um, slot_y))
        slots = gf.Component()
        slots.add_ref(left_slot)
        slots.add_ref(right_slot)
        loaded = gf.boolean(A=body, B=slots, operation="not", layer=LAYER)
        c.add_ref(loaded)

        # Short tapered-looking feeds are formed by straight primitive paths.
        ymid = y0 + loading_body_height_um / 2
        for x0, sign in ((0.45, 1), (2.55, -1)):
            p = gf.path.straight(length=feed_length_um)
            if sign < 0:
                p.drotate(180)
            p.dmove((x0, ymid))
            c.add_ref(p.extrude(width=feed_width_um, layer=LAYER))

    # The trim is deliberately zero in the image-faithful baseline. Increasing
    # delta_length extends one arm by a live, 0.40-um-wide routed section.
    if delta_length > 0:
        trim = gf.path.straight(length=delta_length)
        trim.dmove((1.50, 5.30))
        c.add_ref(trim.extrude(width=loop_width_um, layer=LAYER))
    return c


if __name__ == "__main__":
    component = loop_loaded_device().copy()
    component.flatten()
    component.write_gds(Path(__file__).with_name("device.gds"))
    reference_arm = gf.path.straight(length=1.0)
    trimmed_arm = gf.path.straight(length=1.0 + delta_length)
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(
            {
                "arms": {"reference": reference_arm.length(), "trimmed": trimmed_arm.length()},
                "delta_length_um": trimmed_arm.length() - reference_arm.length(),
            },
            indent=2,
        )
    )
