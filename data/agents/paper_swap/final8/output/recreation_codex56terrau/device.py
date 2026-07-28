from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Global device dimensions and function-defining geometry knobs (um).
device_length = 120.0
device_width = 4.0
outer_taper_length = 1.732
inner_taper_length = 1.231
outer_rail_width = 1.375
inner_rail_width = 1.360
outer_body_width = 99.734
inner_body_width = 99.734
outer_tip_width = 111.604
inner_tip_width = 107.058
coupler_gap = 0.030
inner_rung_width = 0.066
inner_rung_pitch = 0.1004
inner_rung_count = 5
central_rail_width = 0.066
central_outer_rail_width = 0.070
central_middle_rail_width = 0.060
central_rail_pitch = 0.1004
central_first_y = 1.7924
transfer_length = 0.10
reference_bar_length = 119.90
layout_center_x = 59.94

# Width samples of the curved upper profiles.  Consecutive primitive tapers
# reproduce the visibly slow initial flare and the sharper turn near the body.
outer_profile_knots = (
    (0.000, outer_tip_width),
    (0.100, 111.256),
    (0.200, 110.940),
    (0.300, 110.592),
    (0.400, 110.244),
    (0.500, 109.840),
    (0.600, 109.432),
    (0.700, 109.028),
    (0.800, 108.624),
    (0.900, 108.160),
    (1.000, 107.668),
    (1.100, 107.146),
    (1.200, 106.568),
    (1.250, 106.250),
    (1.263, 106.150),
    (1.300, 105.930),
    (1.400, 105.178),
    (1.500, 104.310),
    (1.600, 103.208),
    (1.700, 101.472),
    (outer_taper_length, outer_body_width),
)
outer_opening_knots = (
    (0.000, outer_tip_width - 2 * outer_rail_width),
    (0.100, 108.478),
    (0.200, 108.072),
    (0.300, 107.696),
    (0.400, 107.270),
    (0.500, 106.826),
    (0.600, 106.336),
    (0.700, 105.784),
    (0.800, 105.206),
    (0.900, 104.594),
    (1.000, 103.816),
    (1.100, 102.920),
    (1.200, 101.616),
    (1.230, 100.820),
    (1.250, 100.400),
    (1.260, 99.792),
    (1.263, 99.700),
)
inner_profile_knots = (
    (0.000, inner_tip_width),
    (0.100, 106.740),
    (0.200, 106.422),
    (0.300, 106.076),
    (0.400, 105.786),
    (0.500, 105.496),
    (0.600, 105.092),
    (0.700, 104.684),
    (0.750, 104.454),
    (0.800, 104.224),
    (0.900, 103.702),
    (1.000, 103.092),
    (1.100, 102.252),
    (1.200, 100.980),
    (inner_taper_length, inner_body_width),
)
inner_opening_knots = (
    (0.000, inner_tip_width - 2 * inner_rail_width),
    (0.100, 104.020),
    (0.200, 103.702),
    (0.300, 103.324),
    (0.400, 102.890),
    (0.500, 102.368),
    (0.600, 101.732),
    (0.700, 100.806),
    (0.750, 100.024),
    (0.800, 100.120),
    (0.900, 100.020),
    (1.000, 99.760),
    (1.100, 99.580),
    (1.200, 99.420),
    (inner_taper_length, 99.100),
)


@gf.cell
def vertical_taper(height: float, bottom_width: float, top_width: float, x_center: float, y0: float):
    """A centered taper running upward from y0 to y0 + height."""
    c = gf.Component()
    taper = gf.components.taper(
        length=height,
        width1=top_width,
        width2=bottom_width,
        layer=LAYER,
    )
    ref = c.add_ref(taper)
    ref.drotate(90)
    ref.dmove((x_center, y0))
    return c


@gf.cell
def tapered_profile(knots: tuple[tuple[float, float], ...]):
    """Piecewise-tapered symmetric profile made solely from taper primitives."""
    c = gf.Component()
    for (y0, top_width), (y1, bottom_width) in zip(knots, knots[1:]):
        c.add_ref(
            vertical_taper(
                height=y1 - y0,
                bottom_width=bottom_width,
                top_width=top_width,
                x_center=layout_center_x,
                y0=y0,
            )
        )
    return c


@gf.cell
def top_half():
    """Nested tapered frame and five-rung transfer ladder for the upper half."""
    c = gf.Component()
    outer = tapered_profile(outer_profile_knots)
    outer_opening = tapered_profile(outer_opening_knots)
    c.add_ref(gf.boolean(outer, outer_opening, operation="not", layer=LAYER))

    inner = tapered_profile(inner_profile_knots)
    inner_opening = tapered_profile(inner_opening_knots)
    c.add_ref(gf.boolean(inner, inner_opening, operation="not", layer=LAYER))

    rung_y0 = 0.7980 + coupler_gap - 0.030
    rung_left0 = 7.76
    rung_slope = 3.89
    for index in range(inner_rung_count):
        y = rung_y0 + index * inner_rung_pitch
        left = rung_left0 + (y - rung_y0) * rung_slope
        right = device_length - left
        path = gf.Path([(left, y), (right, y)])
        c.add_ref(path.extrude(width=inner_rung_width, layer=LAYER))
    return c


reference_arm_path = gf.Path(
    [(0.0, central_first_y + central_rail_pitch), (reference_bar_length, central_first_y + central_rail_pitch)]
)
transfer_arm_path = gf.Path(
    [(0.0, central_first_y), (reference_bar_length + transfer_length, central_first_y)]
)


@gf.cell
def recreate_device():
    c = gf.Component()
    upper = c.add_ref(top_half())
    lower = c.add_ref(top_half())
    lower.dmirror(p1=(0.0, device_width / 2), p2=(1.0, device_width / 2))

    rail_paths = [
        transfer_arm_path,
        reference_arm_path,
        gf.Path([(0.0, central_first_y + 2 * central_rail_pitch), (device_length, central_first_y + 2 * central_rail_pitch)]),
        gf.Path([(0.0, central_first_y + 3 * central_rail_pitch), (device_length, central_first_y + 3 * central_rail_pitch)]),
        gf.Path([(0.0, central_first_y + 4 * central_rail_pitch), (device_length, central_first_y + 4 * central_rail_pitch)]),
    ]
    rail_widths = [
        central_outer_rail_width,
        central_rail_width,
        central_middle_rail_width,
        central_rail_width,
        central_outer_rail_width,
    ]
    for path, width in zip(rail_paths, rail_widths):
        c.add_ref(path.extrude(width=width, layer=LAYER))
    return c


component = recreate_device()
output_dir = Path(__file__).resolve().parent
lengths = {
    "arms": {
        "reference": float(reference_arm_path.length()),
        "transfer": float(transfer_arm_path.length()),
    },
    "delta_length_um": float(abs(transfer_arm_path.length() - reference_arm_path.length())),
}
(output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
component.write_gds(output_dir / "device.gds", with_metadata=False)
