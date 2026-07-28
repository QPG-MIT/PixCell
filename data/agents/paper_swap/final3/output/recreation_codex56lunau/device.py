import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Geometry contract: all dimensions are in microns and all material is layer (1, 0).
layer = (1, 0)
footprint_height = 4.0
port_width = 0.30
wide_width = 0.40
narrow_width = 0.20
coupler_gap = 0.16
transfer_length = 57.0
lower_transfer_length = 57.0
taper_length = 10.0
bend_radius = 7.5
s_bend_length = 15.0
lead_length = 5.0
output_lead_length = 18.0
interaction_center_y = 1.99
input_port_offset = 0.27
output_port_shift = 0.10


def cubic_s_bend(length: float, offset: float, npoints: int = 121) -> gf.Path:
    """Return a horizontal-facing S-bend centerline fitted to the raster."""
    t = np.linspace(0.0, 1.0, npoints)
    # The source bend has a long shallow entry, a compact steep turn, and a
    # horizontal exit. Both exponents remain >1 so the ends are tangent to
    # the adjoining straight sections; bend_radius is a live shape knob.
    alpha = 2.12 + 0.05 * (7.5 - bend_radius)
    beta = 1.33 + 0.05 * (bend_radius - 7.5)
    weight = 2.0525
    numerator = t**alpha
    profile = numerator / (numerator + weight * (1.0 - t) ** beta)
    path = gf.Path(np.column_stack((length * t, offset * profile)))
    path.start_angle = 0.0
    path.end_angle = 0.0
    return path


def standard_s_bend(length: float, offset: float, npoints: int = 121) -> gf.Path:
    """Return the compact, symmetric exit S-bend seen at the right side."""
    t = np.linspace(0.0, 1.0, npoints)
    profile = 3.0 * t**2 - 2.0 * t**3
    path = gf.Path(np.column_stack((length * t, offset * profile)))
    path.start_angle = 0.0
    path.end_angle = 0.0
    return path


def centerline(
    start_y: float,
    first_offset: float,
    second_offset: float,
    middle_length: float,
) -> gf.Path:
    """Build the same path used by the assembled geometry for measurement."""
    path = gf.Path([(0.0, start_y), (lead_length, start_y)])
    path += gf.path.straight(taper_length)
    path += cubic_s_bend(s_bend_length, first_offset)
    path += gf.path.straight(middle_length)
    path += standard_s_bend(s_bend_length, second_offset)
    path += gf.path.straight(output_lead_length)
    return path


@gf.cell
def device() -> gf.Component:
    """Assemble the two tapered, asymmetric directional-coupler guides."""
    c = gf.Component("asymmetric_directional_coupler")

    xs_port = gf.cross_section.cross_section(width=port_width, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=wide_width, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=narrow_width, layer=layer)
    xs_upper_end = gf.cross_section.cross_section(width=0.31, layer=layer)
    xs_lower_end = gf.cross_section.cross_section(width=0.29, layer=layer)

    center_separation = 0.5 * (wide_width + narrow_width) + coupler_gap
    center_y = interaction_center_y
    # The absolute rasterizer flips GDS y into image rows.  Keep the visible
    # upper, wider guide at the larger GDS-y coordinate.
    upper_center_y = center_y + 0.5 * center_separation
    lower_center_y = center_y - 0.5 * center_separation

    upper_input_y = footprint_height - input_port_offset
    lower_input_y = input_port_offset
    upper_output_y = footprint_height - (input_port_offset - output_port_shift)
    lower_output_y = input_port_offset - output_port_shift

    # Upper guide: port -> wide taper -> S-bend -> adiabatic exchange -> port.
    upper_lead_l = c << gf.path.extrude(gf.path.straight(lead_length), cross_section=xs_port)
    upper_lead_l.move((0.0, upper_input_y))
    upper_taper_l = c << gf.path.extrude_transition(
        gf.path.straight(taper_length),
        gf.path.transition(xs_port, xs_wide, width_type="linear"),
    )
    upper_taper_l.connect("o1", upper_lead_l.ports["o2"])
    upper_s_l = c << gf.path.extrude(
        cubic_s_bend(s_bend_length, upper_center_y - upper_input_y), cross_section=xs_wide
    )
    upper_s_l.connect("o1", upper_taper_l.ports["o2"])
    upper_center = c << gf.path.extrude_transition(
        gf.path.straight(transfer_length),
        gf.path.transition(xs_wide, xs_upper_end, width_type="linear"),
    )
    upper_center.connect("o1", upper_s_l.ports["o2"])
    upper_s_r = c << gf.path.extrude_transition(
        standard_s_bend(s_bend_length, upper_output_y - upper_center_y),
        gf.path.transition(xs_upper_end, xs_port, width_type="linear"),
    )
    upper_s_r.connect("o1", upper_center.ports["o2"])
    upper_lead_r = c << gf.path.extrude(
        gf.path.straight(output_lead_length), cross_section=xs_port
    )
    upper_lead_r.connect("o1", upper_s_r.ports["o2"])

    # Lower guide: the narrower input exchanges into the common output width.
    lower_lead_l = c << gf.path.extrude(gf.path.straight(lead_length), cross_section=xs_port)
    lower_lead_l.move((0.0, lower_input_y))
    lower_taper_l = c << gf.path.extrude_transition(
        gf.path.straight(taper_length),
        gf.path.transition(xs_port, xs_narrow, width_type="linear"),
    )
    lower_taper_l.connect("o1", lower_lead_l.ports["o2"])
    lower_s_l = c << gf.path.extrude(
        cubic_s_bend(s_bend_length, lower_center_y - lower_input_y), cross_section=xs_narrow
    )
    lower_s_l.connect("o1", lower_taper_l.ports["o2"])
    lower_center = c << gf.path.extrude_transition(
        gf.path.straight(lower_transfer_length),
        gf.path.transition(xs_narrow, xs_lower_end, width_type="linear"),
    )
    lower_center.connect("o1", lower_s_l.ports["o2"])
    lower_s_r = c << gf.path.extrude_transition(
        standard_s_bend(s_bend_length, lower_output_y - lower_center_y),
        gf.path.transition(xs_lower_end, xs_port, width_type="linear"),
    )
    lower_s_r.connect("o1", lower_center.ports["o2"])
    lower_lead_r = c << gf.path.extrude(
        gf.path.straight(output_lead_length), cross_section=xs_port
    )
    lower_lead_r.connect("o1", lower_s_r.ports["o2"])

    return c


out_dir = Path(__file__).parent
component = device()
center_separation = 0.5 * (wide_width + narrow_width) + coupler_gap
upper_center_y = interaction_center_y + 0.5 * center_separation
lower_center_y = interaction_center_y - 0.5 * center_separation
upper_path = centerline(
    footprint_height - input_port_offset,
    upper_center_y - (footprint_height - input_port_offset),
    (footprint_height - (input_port_offset - output_port_shift)) - upper_center_y,
    transfer_length,
)
lower_path = centerline(
    input_port_offset,
    lower_center_y - input_port_offset,
    (input_port_offset - output_port_shift) - lower_center_y,
    lower_transfer_length,
)
upper_length = upper_path.length()
lower_length = lower_path.length()
(out_dir / "lengths.json").write_text(
    json.dumps(
        {
            "arms": {"upper": upper_length, "lower": lower_length},
            "delta_length_um": upper_length - lower_length,
            "coupler": {
                "length_um": transfer_length,
                "gap_um": coupler_gap,
                "width_um": wide_width,
            },
        },
        indent=2,
    )
)
component.write_gds(out_dir / "device.gds", with_metadata=False)
