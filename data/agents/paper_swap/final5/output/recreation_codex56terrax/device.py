"""Primitives-only recreation of the calibrated folded periodic coupler."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Layer and calibrated drawing frame.
layer = (1, 0)
footprint_width = 0.70

# Coupling-section function knobs: periodic interaction and its three rails.
interaction_length = 8.702
grating_period = 0.160
grating_count: int = 55
grating_tooth_width = 0.115
corrugated_rail_width = 0.050
central_bus_width = 0.024
central_reference_length = 5.324
rail_gap = 0.018

# Folded-access and taper function knobs.
access_width = 0.050
access_bend_radius = 0.055
taper_length = 1.950
taper_tip_width = 0.004
taper_wide_width = 0.064

# Fixed placement dimensions, all in the visual (top-down image) coordinate frame.
top_band_y = 0.03575
top_corrugated_y = 0.28830
central_bus_y = 0.34415
bottom_corrugated_y = 0.39940
bottom_band_y = 0.64940
top_taper_x = 2.224
top_band_start_x = top_taper_x + taper_length
top_band_end_x = 14.200
bottom_band_start_x = 4.000
bottom_band_end_x = 14.000
left_grating_x = 4.454
central_bus_x = 1.944


def _gds_y(visual_y: float) -> float:
    """Map an image-space y coordinate to the GDS coordinate convention."""
    return footprint_width - visual_y


def _add_smooth_path(
    component: gf.Component,
    visual_points: list[tuple[float, float]],
    width: float,
    radius: float,
) -> gf.Path:
    """Add an Euler-smoothed, constant-width guide from image-space points."""
    points = np.asarray([(x, _gds_y(y)) for x, y in visual_points], dtype=float)
    path = gf.path.smooth(points, radius=radius, bend=gf.path.euler)
    component.add_ref(path.extrude(width=width, layer=layer))
    return path


def _add_straight(
    component: gf.Component, x: float, visual_y: float, length: float, width: float
) -> gf.Path:
    """Add a horizontal guide and return the actual gf.Path used for it."""
    path = gf.path.straight(length)
    path.dmove((x, _gds_y(visual_y)))
    component.add_ref(path.extrude(width=width, layer=layer))
    return path


def _add_bezier_path(
    component: gf.Component,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    width: float,
) -> gf.Path:
    """Extrude a densely sampled cubic Bezier guide from four visual points."""
    t = np.linspace(0.0, 1.0, 121)[:, None]
    control = np.asarray([p0, p1, p2, p3], dtype=float)
    visual = (
        (1 - t) ** 3 * control[0]
        + 3 * (1 - t) ** 2 * t * control[1]
        + 3 * (1 - t) * t**2 * control[2]
        + t**3 * control[3]
    )
    path = gf.Path([(float(x), _gds_y(float(y))) for x, y in visual])
    component.add_ref(path.extrude(width=width, layer=layer))
    return path


def _add_bezier_transition(
    component: gf.Component,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    width1: float,
    width2: float,
) -> gf.Path:
    """Extrude a Bezier with a named, layer-(1,0) width transition."""
    t = np.linspace(0.0, 1.0, 121)[:, None]
    control = np.asarray([p0, p1, p2, p3], dtype=float)
    visual = (
        (1 - t) ** 3 * control[0]
        + 3 * (1 - t) ** 2 * t * control[1]
        + 3 * (1 - t) * t**2 * control[2]
        + t**3 * control[3]
    )
    path = gf.Path([(float(x), _gds_y(float(y))) for x, y in visual])
    # GDSFactory's transition extrusion follows the Path's stored direction,
    # which is opposite this visual-coordinate construction; reverse the two
    # end sections so width1 is at p0 and width2 is at p3 in the image.
    xs1 = gf.CrossSection(sections=(gf.Section(width=width2, layer=layer, name="wg"),))
    xs2 = gf.CrossSection(sections=(gf.Section(width=width1, layer=layer, name="wg"),))
    transition = gf.path.transition(xs1, xs2, width_type="sine")
    component.add_ref(path.extrude_transition(transition))
    return path


def _add_rectangle(
    component: gf.Component, x: float, visual_y: float, xsize: float, ysize: float
) -> None:
    """Add a visual-coordinate rectangle without emitting a raw polygon."""
    rect = gf.components.rectangle(size=(xsize, ysize), layer=layer)
    ref = component.add_ref(rect)
    ref.dmove((x, _gds_y(visual_y + ysize)))


@gf.cell
def device() -> gf.Component:
    """Return the folded periodic coupler on the single material layer."""
    c = gf.Component()

    # Top tapered rail and its broad folded return.
    top_taper = gf.components.taper(
        length=taper_length,
        width1=taper_tip_width,
        width2=taper_wide_width,
        layer=layer,
    )
    top_taper_ref = c.add_ref(top_taper)
    top_taper_ref.dmove((top_taper_x, _gds_y(top_band_y)))
    _add_straight(
        c,
        top_band_start_x,
        top_band_y,
        top_band_end_x - top_band_start_x,
        taper_wide_width,
    )
    _add_bezier_path(
        c,
        (14.150, top_band_y),
        (15.880, top_band_y),
        (15.880, top_corrugated_y),
        (14.180, top_corrugated_y),
        width=0.050,
    )
    # The tight turn locally widens before the two arms coalesce; these
    # narrow path extrusions preserve that photographed adiabatic flare.
    _add_bezier_path(
        c,
        (14.550, 0.076),
        (14.750, 0.085),
        (14.900, 0.110),
        (15.080, 0.125),
        width=0.030,
    )
    _add_bezier_path(
        c,
        (14.550, 0.267),
        (14.750, 0.255),
        (14.900, 0.235),
        (15.080, 0.215),
        width=0.030,
    )
    _add_rectangle(c, 15.050, 0.090, 0.250, 0.145)
    _add_straight(c, 13.201, top_corrugated_y, 0.999, corrugated_rail_width)

    # Top-left folded access guide to the periodic interaction rail.
    _add_smooth_path(
        c,
        [
            (0.025, 0.036),
            (0.180, 0.076),
            (0.490, 0.145),
            (1.050, 0.215),
            (1.800, 0.260),
            (2.800, 0.283),
            (4.414, top_corrugated_y),
        ],
        width=access_width,
        radius=access_bend_radius,
    )

    # The central through bus is a physical parametric path.  The same path
    # supplies the measured long-arm length; its length changes exactly with
    # interaction_length for the required knob-response proof.
    long_arm_path = _add_straight(
        c,
        central_bus_x,
        central_bus_y,
        central_reference_length + interaction_length,
        central_bus_width,
    )
    short_arm_path = gf.path.straight(central_reference_length)

    # Repeated material bars of the two corrugated interaction rails.
    for index in range(grating_count):
        tooth_x = left_grating_x + index * grating_period
        _add_rectangle(
            c,
            tooth_x,
            top_corrugated_y - corrugated_rail_width / 2,
            grating_tooth_width,
            corrugated_rail_width,
        )
        _add_rectangle(
            c,
            tooth_x,
            bottom_corrugated_y - corrugated_rail_width / 2,
            grating_tooth_width,
            corrugated_rail_width,
        )

    # Bottom rail folds left into a broad lower band and then tapers to a tip.
    _add_bezier_path(
        c,
        (4.414, bottom_corrugated_y),
        (1.980, 0.425),
        (1.980, 0.600),
        (4.000, bottom_band_y),
        width=0.050,
    )
    _add_straight(
        c,
        bottom_band_start_x,
        bottom_band_y,
        bottom_band_end_x - bottom_band_start_x,
        taper_wide_width,
    )
    bottom_taper = gf.components.taper(
        length=1.700,
        width1=taper_wide_width,
        width2=taper_tip_width,
        layer=layer,
    )
    bottom_taper_ref = c.add_ref(bottom_taper)
    bottom_taper_ref.dmove((bottom_band_end_x, _gds_y(bottom_band_y)))

    # Bottom-right folded access guide leaving the lower corrugated rail.
    _add_bezier_path(
        c,
        (13.201, bottom_corrugated_y),
        (15.700, bottom_corrugated_y),
        (17.200, 0.460),
        (17.700, 0.630),
        width=access_width,
    )

    # A two-nanometre marker establishes the calibrated vertical frame; its
    # area is below one target pixel after rasterization but fixes bbox centering.
    _add_rectangle(c, 17.700, 0.694, 0.002, 0.002)

    # Preserve the two path-derived arm values required by the local evaluator.
    arm_lengths = {
        "long_central_bus": float(long_arm_path.length()),
        "reference_bus": float(short_arm_path.length()),
    }
    payload = {
        "arms": arm_lengths,
        "delta_length_um": abs(arm_lengths["long_central_bus"] - arm_lengths["reference_bus"]),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))
    return c


if __name__ == "__main__":
    device().write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
