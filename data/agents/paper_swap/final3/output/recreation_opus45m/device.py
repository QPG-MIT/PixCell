"""Directional coupler 2x2 - two waveguides with S-bend transitions to coupling region."""
import gdsfactory as gf
from gdsfactory.typings import LayerSpec

# Tunables - function-defining knobs
waveguide_width = 0.5
coupling_length = 38.0
coupling_gap = 0.12
sbend_length = 33.0
port_separation = 3.5

# Derived
total_length = 120.0
input_straight = (total_length - coupling_length - 2 * sbend_length) / 2

LAYER: LayerSpec = (1, 0)


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()

    xs = gf.cross_section.cross_section(width=waveguide_width, layer=LAYER)

    # S-bend vertical displacement: from port to coupling region
    coupling_center_y = (coupling_gap + waveguide_width) / 2
    sbend_dy = port_separation / 2 - coupling_center_y

    # Create components
    straight_in = gf.components.straight(length=input_straight, cross_section=xs)
    straight_coupling = gf.components.straight(length=coupling_length, cross_section=xs)
    straight_out = gf.components.straight(length=input_straight, cross_section=xs)

    # Top arm
    top_y = port_separation / 2
    sbend_top_down = gf.components.bend_s(size=(sbend_length, -sbend_dy), cross_section=xs)
    sbend_top_up = gf.components.bend_s(size=(sbend_length, sbend_dy), cross_section=xs)

    top_in = c << straight_in
    top_in.dmovey(top_y)

    top_sb1 = c << sbend_top_down
    top_sb1.connect("o1", top_in.ports["o2"])

    top_coup = c << straight_coupling
    top_coup.connect("o1", top_sb1.ports["o2"])

    top_sb2 = c << sbend_top_up
    top_sb2.connect("o1", top_coup.ports["o2"])

    top_out = c << straight_out
    top_out.connect("o1", top_sb2.ports["o2"])

    # Bottom arm
    bottom_y = -port_separation / 2
    sbend_bot_up = gf.components.bend_s(size=(sbend_length, sbend_dy), cross_section=xs)
    sbend_bot_down = gf.components.bend_s(size=(sbend_length, -sbend_dy), cross_section=xs)

    bottom_in = c << straight_in
    bottom_in.dmovey(bottom_y)

    bot_sb1 = c << sbend_bot_up
    bot_sb1.connect("o1", bottom_in.ports["o2"])

    bot_coup = c << straight_coupling
    bot_coup.connect("o1", bot_sb1.ports["o2"])

    bot_sb2 = c << sbend_bot_down
    bot_sb2.connect("o1", bot_coup.ports["o2"])

    bot_out = c << straight_out
    bot_out.connect("o1", bot_sb2.ports["o2"])

    return c


if __name__ == "__main__":
    c = directional_coupler()
    c.write_gds("experiments/paper_swap/final3/output/recreation_opus45m/device.gds")
    print(f"Written device.gds, size: {c.dxsize:.2f} x {c.dysize:.2f} um")
