import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)
footprint = 4.7
guide_width = 0.236
access_length = 0.55
fixed_access_length = 0.55
outer_taper_length = 0.98
inner_taper_length = 0.82
crossing_max_width = 0.93
center_width = 0.56


def smooth_transition(
    length: float, width1: float, width2: float
) -> tuple[gf.Component, gf.Path]:
    """Extrudes a sine-width transition using only a straight Path."""
    xs1 = gf.cross_section.cross_section(width=width1, layer=layer)
    xs2 = gf.cross_section.cross_section(width=width2, layer=layer)
    transition = gf.path.transition(xs1, xs2, width_type="sine")
    path = gf.Path()
    path.append(gf.path.straight(length=length, npoints=101))
    return gf.path.extrude_transition(path, transition), path


def half_arm(access_len: float) -> tuple[gf.Component, float]:
    """Build one radial arm and measure its centerline from its actual Paths."""
    arm = gf.Component()
    inner, inner_path = smooth_transition(
        length=inner_taper_length,
        width1=center_width,
        width2=crossing_max_width,
    )
    outer, outer_path = smooth_transition(
        length=outer_taper_length,
        width1=crossing_max_width,
        width2=guide_width,
    )
    access_path = gf.path.straight(length=access_len)
    access = gf.path.extrude(
        access_path,
        layer=layer,
        width=guide_width,
    )

    center = arm.add_ref(inner)
    taper = arm.add_ref(outer)
    lead = arm.add_ref(access)
    taper.connect("o1", center.ports["o2"])
    lead.connect("o1", taper.ports["o2"])

    measured_length = inner_path.length() + outer_path.length() + access_path.length()
    return arm, measured_length


@gf.cell
def crossing() -> gf.Component:
    c = gf.Component()

    east_arm, east_length = half_arm(access_length)
    fixed_arm, fixed_length = half_arm(fixed_access_length)

    east = c.add_ref(east_arm)
    east.rotate(0)
    for rotation in (90, 180, 270):
        arm = c.add_ref(fixed_arm)
        arm.rotate(rotation)

    c.info["east_length_um"] = east_length
    c.info["west_length_um"] = fixed_length

    return c


component = crossing()
component.write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
east_length = float(component.info["east_length_um"])
west_length = float(component.info["west_length_um"])
Path(__file__).with_name("lengths.json").write_text(
    json.dumps(
        {
            "arms": {"east": east_length, "west": west_length},
            "delta_length_um": abs(east_length - west_length),
        },
        indent=2,
    )
)
