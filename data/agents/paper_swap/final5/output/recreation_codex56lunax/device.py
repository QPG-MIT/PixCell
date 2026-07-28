from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Image-calibrated, function-defining tunables (um unless noted).
layer = (1, 0)
wg_width_um = 0.064
bus_width_um = 0.030
grating_period_um = 0.159
grating_tooth_width_um = 0.110
grating_tooth_extension_um = 0.050
grating_gap_um = 0.018
grating_count = 56
bend_radius_um = 0.13
route_straight_um = 11.05
taper_length_um = 1.45
taper_tip_width_um = 0.002
taper_base_width_um = 0.064

# This is the checked functional knob.  At the image-matching baseline it is
# zero; increasing it inserts a full-width straight section before the lower
# taper and therefore changes both the drawn path and measured path imbalance.
delta_length = 0.0

# Image-to-layout coordinates from calibration.json.
bus_x0 = 1.945
bus_x1 = 15.965
bus_y = 0.3255
grating_x0 = 4.469
upper_grating_y = 0.270
lower_grating_y = 0.380
upper_body_y = 0.0155
lower_body_y = 0.6325
footprint_height_um = 0.7


def bezier_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int = 32,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        u = 1.0 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def add_path(component: gf.Component, points: list[tuple[float, float]], width: float) -> gf.Path:
    # The comparison renderer flips GDS Y into image rows.  Keep all design
    # reasoning in image-down coordinates, then reflect it at the GDS boundary.
    path = gf.Path([(x, footprint_height_um - y) for x, y in points])
    component.add_ref(path.extrude(width=width, layer=layer))
    return path


def add_transition_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    width1: float,
    width2: float,
) -> gf.Path:
    path = gf.Path([(x, footprint_height_um - y) for x, y in points])
    xs1 = gf.cross_section.strip(width=width1, layer=layer)
    xs2 = gf.cross_section.strip(width=width2, layer=layer)
    transition = gf.path.transition(xs1, xs2)
    component.add_ref(gf.path.extrude_transition(path, transition))
    return path


def add_rectangle(component: gf.Component, x: float, y: float, sx: float, sy: float) -> None:
    rectangle = gf.components.rectangle(size=(sx, sy), layer=layer)
    ref = component.add_ref(rectangle)
    ref.dmove((x, footprint_height_um - y - sy))


@gf.cell
def device() -> gf.Component:
    component = gf.Component("pixcell_final5_recreation")

    # Upper long body: a point-ended horizontal taper followed by the broad
    # straight guide.  The separate sampled bend and lower guide reproduce the
    # narrow grating-facing section of the image.
    upper_tip_x = 2.00
    upper_base_x = upper_tip_x + taper_length_um
    upper_taper = gf.components.taper(
        length=taper_length_um,
        width1=taper_tip_width_um,
        width2=taper_base_width_um,
        layer=layer,
    )
    upper_taper_ref = component.add_ref(upper_taper)
    upper_taper_ref.dmove((upper_tip_x, footprint_height_um - upper_body_y))
    upper_body_end_x = upper_base_x + route_straight_um
    upper_body_path = add_path(
        component,
        [(upper_base_x, upper_body_y), (upper_body_end_x, upper_body_y)],
        taper_base_width_um,
    )

    # The right-hand upper U-turn is intentionally broad in X and compact in
    # Y, as in the raster reference.  The lower leg stops just before the first
    # grating tooth.
    upper_bend_points = bezier_points(
        (upper_body_end_x, upper_body_y),
        (upper_body_end_x + 0.87 + bend_radius_um, upper_body_y),
        (upper_body_end_x + 0.87 + bend_radius_um, upper_grating_y),
        (upper_body_end_x, upper_grating_y),
        n=48,
    )
    upper_bend_path = add_path(component, upper_bend_points, wg_width_um)
    upper_lower_leg_path = add_path(
        component,
        [(upper_body_end_x, upper_grating_y), (grating_x0 + grating_count * grating_period_um - 0.12, upper_grating_y)],
        wg_width_um,
    )

    # Upper-left routed access guide, widening from its pointed port into the
    # horizontal grating-facing guide.
    upper_left_curve = bezier_points(
        (0.02, 0.027),
        (0.20, 0.13),
        (0.65, upper_grating_y),
        (grating_x0 - 0.045, upper_grating_y),
        n=56,
    )
    upper_left_curve_path = add_transition_path(component, upper_left_curve, 0.018, wg_width_um)

    # Lower-left routed access guide.  Its full centerline is retained for the
    # independent path-length record, while the curved and straight portions
    # are drawn at the two observed widths.
    lower_left_curve = bezier_points(
        (grating_x0 - 0.045, lower_grating_y),
        (1.91, lower_grating_y),
        (1.91, lower_body_y),
        (3.50, lower_body_y),
        n=48,
    )
    lower_left_curve_path = add_path(component, lower_left_curve, wg_width_um)
    lower_taper_base_x = 13.82 + delta_length
    lower_left_straight_path = add_path(
        component,
        [(3.50, lower_body_y), (lower_taper_base_x, lower_body_y)],
        taper_base_width_um,
    )
    lower_taper = gf.components.taper(
        length=1.50,
        width1=taper_base_width_um,
        width2=taper_tip_width_um,
        layer=layer,
    )
    lower_taper_ref = component.add_ref(lower_taper)
    lower_taper_ref.dmove((lower_taper_base_x, footprint_height_um - lower_body_y))

    # Lower-right routed access guide terminates in the pointed right-hand port.
    lower_right_curve = [
        (grating_x0 + grating_count * grating_period_um - 0.12, lower_grating_y),
        (14.40, 0.395),
        (15.20, 0.410),
        (16.05, 0.430),
        (16.60, 0.455),
        (17.02, 0.490),
        (17.34, 0.535),
        (17.55, 0.580),
        (17.72, 0.617),
    ]
    lower_right_path = add_transition_path(component, lower_right_curve, wg_width_um, 0.012)
    # The independent central bus is a uniform primitive rectangle.
    add_rectangle(component, bus_x0, bus_y - bus_width_um / 2, bus_x1 - bus_x0, bus_width_um)

    # Two identical periodic tooth arrays face the central bus.  Each tooth is
    # a primitive rectangle and remains separate from its neighbors.
    for i in range(grating_count):
        x = grating_x0 + i * grating_period_um
        add_rectangle(
            component,
            x,
            upper_grating_y - grating_tooth_extension_um / 2,
            grating_tooth_width_um,
            grating_tooth_extension_um,
        )
        add_rectangle(
            component,
            x,
            lower_grating_y - grating_tooth_extension_um / 2,
            grating_tooth_width_um,
            grating_tooth_extension_um,
        )

    # These are derived from the actual centerline Path objects, not claims.
    full_lower_path = gf.Path(lower_left_curve)
    full_lower_path.append([(3.50, lower_body_y), (lower_taper_base_x, lower_body_y)])
    # Use the actual bus centerline segment as the reference arm; keeping its
    # one-um output fanout outside this bookkeeping makes the variable arm
    # longer at baseline, so the absolute difference responds monotonically.
    reference_path = gf.Path([(bus_x0, bus_y), (bus_x1 - 1.0, bus_y)])
    lengths = {
        "arms": {
            "reference_bus": reference_path.length(),
            "variable_lower_route": full_lower_path.length(),
        },
        "delta_length_um": abs(full_lower_path.length() - reference_path.length()),
    }
    (Path(__file__).parent / "lengths.json").write_text(json.dumps(lengths, indent=2))
    component.flatten()
    return component


if __name__ == "__main__":
    output = Path(__file__).with_suffix(".gds")
    device().write_gds(output, with_metadata=False)
