"""Adiabatic Mode Coupler - Primitives-only GDSFactory implementation.

From image analysis:
- Top waveguide: starts top-left, S-bends down to coupling region, S-bends back up to exit top-right
- Middle waveguide: straight taper from full width to tip, terminates ~60% into device
- Bottom waveguide: taper start from tip, S-bends up to coupling region, S-bends down to exit bottom-right

The middle waveguide is between the top and bottom paths, all three converge in the coupling region.
"""
import gdsfactory as gf
from gdsfactory.typings import LayerSpec

# === TUNABLE PARAMETERS (function-defining knobs) ===
waveguide_width = 0.32  # µm - main waveguide width
taper_tip_width = 0.06  # µm - taper tip width
coupling_gap = 0.10  # µm - minimum gap between waveguides

# Vertical positions (at input side)
top_input_y = 0.65  # µm - top waveguide Y at left edge
middle_y = 0.15  # µm - middle taper Y position
bottom_input_y = -0.55  # µm - bottom waveguide Y at left edge

# Lengths
left_sbend_length = 18.0  # µm - S-bend approach from left
coupling_length = 4.0  # µm - tight coupling section
right_sbend_length = 18.0  # µm - S-bend exit to right
middle_taper_length = 25.0  # µm - middle taper length
bottom_taper_entry = 8.0  # µm - bottom taper entry length

# === FIXED PARAMETERS ===
LAYER: LayerSpec = (1, 0)


@gf.cell
def adiabatic_mode_coupler() -> gf.Component:
    """Create an adiabatic mode coupler using primitives only."""
    c = gf.Component()

    xs = gf.cross_section.cross_section(
        width=waveguide_width,
        layer=LAYER,
        radius_min=0.5,
    )

    # Coupling Y positions (where all waveguides converge)
    coupling_y = middle_y

    # === TOP WAVEGUIDE ===
    # S-bend from top-left input down toward middle
    top_offset = top_input_y - coupling_y - waveguide_width/2 - coupling_gap/2
    top_sbend1 = c << gf.components.bend_s(
        size=(left_sbend_length, -top_offset),
        cross_section=xs,
    )
    top_sbend1.move((0, top_input_y))

    # Short coupling straight
    top_straight = c << gf.components.straight(length=coupling_length, cross_section=xs)
    top_straight.connect("o1", top_sbend1.ports["o2"])

    # S-bend back up to top-right output
    top_sbend2 = c << gf.components.bend_s(
        size=(right_sbend_length, top_offset),
        cross_section=xs,
    )
    top_sbend2.connect("o1", top_straight.ports["o2"])

    # === MIDDLE WAVEGUIDE (taper to termination) ===
    middle_taper = c << gf.components.taper(
        length=middle_taper_length,
        width1=waveguide_width,
        width2=taper_tip_width,
        layer=LAYER,
    )
    middle_taper.move((0, middle_y))

    # === BOTTOM WAVEGUIDE ===
    # Taper entry from tip
    bottom_taper = c << gf.components.taper(
        length=bottom_taper_entry,
        width1=taper_tip_width,
        width2=waveguide_width,
        layer=LAYER,
    )
    bottom_taper.move((0, bottom_input_y))

    # S-bend up toward coupling region
    bottom_offset = coupling_y - waveguide_width/2 - coupling_gap/2 - bottom_input_y
    bottom_sbend1 = c << gf.components.bend_s(
        size=(left_sbend_length - bottom_taper_entry, bottom_offset),
        cross_section=xs,
    )
    bottom_sbend1.connect("o1", bottom_taper.ports["o2"])

    # Coupling straight
    bottom_straight = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bottom_straight.connect("o1", bottom_sbend1.ports["o2"])

    # S-bend back down to bottom-right output
    bottom_sbend2 = c << gf.components.bend_s(
        size=(right_sbend_length, -bottom_offset),
        cross_section=xs,
    )
    bottom_sbend2.connect("o1", bottom_straight.ports["o2"])

    # Add ports
    c.add_port("o1", port=top_sbend1.ports["o1"])
    c.add_port("o2", port=middle_taper.ports["o1"])
    c.add_port("o3", port=bottom_taper.ports["o1"])
    c.add_port("o4", port=top_sbend2.ports["o2"])
    c.add_port("o5", port=bottom_sbend2.ports["o2"])

    return c


if __name__ == "__main__":
    device = adiabatic_mode_coupler()
    device.write_gds("experiments/paper_swap/final1/output/recreation_opus45m/device.gds")
    print("Generated GDS: device.gds")
