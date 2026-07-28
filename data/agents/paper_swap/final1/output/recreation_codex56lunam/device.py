import json
import gdsfactory as gf


# Geometry is in micrometres and is intentionally exposed as top-level tunables.
layer = (1, 0)
input_width = 0.272
output_width = 0.238
tip_width = 0.074
arm_start_x = 3.05
taper_length = 22.95
arm_separation = 0.540
bend_length = 9.00
bend_offset = 0.465
bend_points = 99
output_straight = 5.00
delta_length = 0.0


@gf.cell
def splitter(
    input_width=input_width,
    output_width=output_width,
    tip_width=tip_width,
    arm_start_x=arm_start_x,
    taper_length=taper_length,
    arm_separation=arm_separation,
    bend_length=bend_length,
    bend_offset=bend_offset,
    bend_points=bend_points,
):
    c = gf.Component()

    # Central input narrows to a pointed termination between the two arms.
    center_taper = c << gf.components.taper(
        length=arm_start_x + taper_length,
        width1=input_width,
        width2=tip_width,
        layer=layer,
    )

    # Mirrored inverse tapers begin a short distance after the input facet.
    arm_taper_top = c << gf.components.taper(
        length=taper_length,
        width1=tip_width,
        width2=output_width,
        layer=layer,
    )
    arm_taper_top.move((arm_start_x, arm_separation / 2))

    arm_taper_bottom = c << gf.components.taper(
        length=taper_length,
        width1=tip_width,
        width2=output_width,
        layer=layer,
    )
    arm_taper_bottom.move((arm_start_x, -arm_separation / 2))

    # Smooth mirrored S-bends carry the widened arms to the output facet.
    bend_top = c << gf.components.bend_s(
        size=(bend_length, bend_offset),
        npoints=bend_points,
        width=output_width,
        cross_section="strip",
    )
    bend_top.connect("o1", arm_taper_top.ports["o2"])

    bend_bottom = c << gf.components.bend_s(
        size=(bend_length, -bend_offset),
        npoints=bend_points,
        width=output_width,
        cross_section="strip",
    )
    bend_bottom.connect("o1", arm_taper_bottom.ports["o2"])

    straight_top = c << gf.components.straight(length=output_straight + delta_length, width=output_width)
    straight_top.connect("o1", bend_top.ports["o2"])
    straight_bottom = c << gf.components.straight(length=output_straight, width=output_width)
    straight_bottom.connect("o1", bend_bottom.ports["o2"])

    c.add_port("in", port=center_taper.ports["o1"])
    c.add_port("out_top", port=straight_top.ports["o2"])
    c.add_port("out_bottom", port=straight_bottom.ports["o2"])
    return c


component = splitter()
component.write_gds("device.gds", with_metadata=False)
nominal_arm_length = taper_length + bend_length + output_straight
with open("lengths.json", "w") as f:
    json.dump(
        {
            "arms": {
                "top": nominal_arm_length + delta_length,
                "bottom": nominal_arm_length,
            },
            "delta_length_um": abs(delta_length),
        },
        f,
    )
