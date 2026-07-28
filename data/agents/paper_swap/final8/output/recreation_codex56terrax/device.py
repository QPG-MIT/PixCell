"""Primitives-only reconstruction of the calibrated multi-rail folded layout."""

from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


# Live, top-level geometric contract (all dimensions are in um).
guide_width = 0.066
guide_pitch = 0.100
central_first_y = 1.806
central_span = 120.0
delta_length = 0.0
bank_start = 10.62
bank_end = 109.38
return_start = 8.92
return_end = 111.08
return_width = 0.468
return_center_offset = 0.502
fanout_start = 6.70
fanout_mid = 8.13
fanout_end = 9.48
fanout_width = 0.670
fanout_tip_width = 0.066
transition_samples = 32
LAYER = (1, 0)


def raised_cosine_route(start: tuple[float, float], end: tuple[float, float]) -> list[tuple[float, float]]:
    """A smooth monotonic centerline used only through gf.Path/extrude."""
    x0, y0 = start
    x1, y1 = end
    points = []
    for index in range(transition_samples + 1):
        t = index / transition_samples
        blend = 0.5 - 0.5 * math.cos(math.pi * t)
        points.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * blend))
    return points


def add_extruded_path(component: gf.Component, points: list[tuple[float, float]], width: float) -> gf.Path:
    """Add a GDSFactory Path extrusion; no hand-authored polygons are emitted."""
    path = gf.Path(points)
    component.add_ref(path.extrude(width=width, layer=LAYER))
    return path


def full_route(
    left: tuple[float, float],
    straight_left: tuple[float, float],
    straight_right: tuple[float, float],
    right: tuple[float, float],
) -> list[tuple[float, float]]:
    """Join two rounded end transitions by an exact horizontal active section."""
    return (
        raised_cosine_route(left, straight_left)
        + [straight_right]
        + raised_cosine_route(straight_right, right)[1:]
    )


def mirrored(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Reflect a centerline about the calibrated 4 um device midline."""
    return [(x, 4.0 - y) for x, y in points]


def add_taper_between(
    component: gf.Component,
    start: tuple[float, float],
    end: tuple[float, float],
    width1: float,
    width2: float,
) -> None:
    """Place a rotated GDSFactory taper between two path-center points."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    taper = gf.components.taper(
        length=math.hypot(dx, dy), width1=width1, width2=width2, layer=LAYER
    )
    reference = component.add_ref(taper)
    reference.drotate(math.degrees(math.atan2(dy, dx)))
    reference.dmove(start)


@gf.cell(check_instances=False)
def folded_multi_rail() -> gf.Component:
    component = gf.Component()
    central_ys = [central_first_y + index * guide_pitch for index in range(5)]
    upper_ys = [0.798 + index * guide_pitch for index in range(5)]
    lower_ys = [3.202 - index * guide_pitch for index in range(5)]

    # The five visible middle rails.  The center rail carries the declared
    # delta_length knob, as a physical straight extension rather than metadata.
    reference_arm = gf.Path([(0.0, central_ys[0]), (central_span, central_ys[0])])
    delayed_arm = gf.Path(
        [(0.0, central_ys[2]), (central_span + delta_length, central_ys[2])]
    )
    component.add_ref(reference_arm.extrude(width=guide_width, layer=LAYER))
    component.add_ref(delayed_arm.extrude(width=guide_width, layer=LAYER))
    for index, y in enumerate(central_ys):
        if index not in (0, 2):
            add_extruded_path(component, [(0.0, y), (central_span, y)], guide_width)

    # Bank rails are separate folded structures, not continuations of the
    # center rails.  Their long sections are parallel, constant-pitch Paths.
    for index in range(5):
        add_extruded_path(component, [(bank_start, upper_ys[index]), (bank_end, upper_ys[index])], guide_width)
        add_extruded_path(component, [(bank_start, lower_ys[index]), (bank_end, lower_ys[index])], guide_width)

    # Each bank opens through a compact tapered feeder at either end.  The
    # short separate tips preserve the five visible rail gaps after the taper.
    top_fanout_left = [
        (fanout_start, -0.180),
        (7.35, 0.100),
        (fanout_mid, 0.580),
        (8.50, 0.750),
    ]
    top_fanout_right = [(central_span - x, y) for x, y in top_fanout_left]
    for points in (top_fanout_left, top_fanout_right):
        add_extruded_path(component, points, fanout_width)
        if points is top_fanout_left:
            add_taper_between(component, points[-1], (fanout_end, 0.960), fanout_width, fanout_tip_width)
        else:
            add_taper_between(component, points[-1], (central_span - fanout_end, 0.960), fanout_width, fanout_tip_width)
    for index, y in enumerate(upper_ys):
        add_extruded_path(component, [(fanout_end, y - 0.035), (bank_start, y)], guide_width)
        add_extruded_path(component, [(bank_end, y), (central_span - fanout_end, y - 0.035)], guide_width)
    for points in (mirrored(top_fanout_left), mirrored(top_fanout_right)):
        add_extruded_path(component, points, fanout_width)
        if points == mirrored(top_fanout_left):
            add_taper_between(component, points[-1], (fanout_end, 3.040), fanout_width, fanout_tip_width)
        else:
            add_taper_between(component, points[-1], (central_span - fanout_end, 3.040), fanout_width, fanout_tip_width)
    for index, y in enumerate(lower_ys):
        add_extruded_path(component, [(fanout_end, y + 0.035), (bank_start, y)], guide_width)
        add_extruded_path(component, [(bank_end, y), (central_span - fanout_end, y + 0.035)], guide_width)

    # Broad upper/lower return rails have a steep-to-shallow end transition.
    top_return_y = 2.0 - return_center_offset
    bottom_return_y = 2.0 + return_center_offset
    top_return_left = [
        (4.20, 0.050),
        (5.24, 0.303),
        (6.69, 0.892),
        (8.13, 1.300),
        (return_start, top_return_y),
    ]
    top_return = (
        top_return_left
        + [(return_end, top_return_y)]
        + [(central_span - x, y) for x, y in reversed(top_return_left)]
    )
    add_extruded_path(
        component,
        top_return,
        return_width,
    )
    add_extruded_path(
        component,
        mirrored(top_return),
        return_width,
    )

    # The metric contract is calculated from the actual two centerline Paths.
    lengths = {
        "arms": {
            "reference": float(reference_arm.length()),
            "delayed": float(delayed_arm.length()),
        },
        "delta_length_um": float(abs(delayed_arm.length() - reference_arm.length())),
    }
    (Path(__file__).parent / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return component


if __name__ == "__main__":
    output_gds = Path(__file__).with_name("device.gds")
    # Keep the physical cell top-level so deterministic area verification can
    # measure layer (1, 0) without traversing GDS metadata context cells.
    folded_multi_rail().write_gds(output_gds, with_metadata=False)
