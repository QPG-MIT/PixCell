import gdsfactory as gf
import numpy as np

# Function-defining tunables
waveguide_width_um = 0.5
coupling_gap_um = 0.35
coupling_length_um = 5.5
port_separation_um = 2.0

# Derived
total_length_um = 18.0
bend_length_um = (total_length_um - coupling_length_um) / 2

LAYER = (1, 0)

def make_cross_section(width):
    return gf.cross_section.cross_section(width=width, layer=LAYER)

@gf.cell
def s_bend(length: float, dy: float, width: float) -> gf.Component:
    """S-bend using sine curve for smooth transition."""
    c = gf.Component()
    npts = 100
    x = np.linspace(0, length, npts)
    y = dy * (1 - np.cos(np.pi * x / length)) / 2
    points = np.column_stack([x, y])
    path = gf.Path(points)
    c << gf.path.extrude(path, cross_section=make_cross_section(width))
    return c

@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()

    # Top arm: starts at y = port_separation_um/2, bends down to y = (coupling_gap_um + waveguide_width_um)/2
    top_y_start = port_separation_um / 2 + waveguide_width_um / 2
    top_y_coupling = (coupling_gap_um + waveguide_width_um) / 2

    # Bottom arm: starts at y = -port_separation_um/2, bends up to y = -(coupling_gap_um + waveguide_width_um)/2
    bot_y_start = -port_separation_um / 2 - waveguide_width_um / 2
    bot_y_coupling = -(coupling_gap_um + waveguide_width_um) / 2

    xs = make_cross_section(waveguide_width_um)

    # S-bend bringing top arm down
    sbend_top_in = s_bend(bend_length_um, -(top_y_start - top_y_coupling), waveguide_width_um)
    ref1 = c << sbend_top_in
    ref1.move((0, top_y_start))

    # Coupling straight for top arm
    coupling_top = gf.components.straight(length=coupling_length_um, cross_section=xs)
    ref2 = c << coupling_top
    ref2.move((bend_length_um, top_y_coupling))

    # S-bend bringing top arm back up
    sbend_top_out = s_bend(bend_length_um, top_y_start - top_y_coupling, waveguide_width_um)
    ref3 = c << sbend_top_out
    ref3.move((bend_length_um + coupling_length_um, top_y_coupling))

    # S-bend bringing bottom arm up
    sbend_bot_in = s_bend(bend_length_um, -(bot_y_start - bot_y_coupling), waveguide_width_um)
    ref4 = c << sbend_bot_in
    ref4.move((0, bot_y_start))

    # Coupling straight for bottom arm
    coupling_bot = gf.components.straight(length=coupling_length_um, cross_section=xs)
    ref5 = c << coupling_bot
    ref5.move((bend_length_um, bot_y_coupling))

    # S-bend bringing bottom arm back down
    sbend_bot_out = s_bend(bend_length_um, bot_y_start - bot_y_coupling, waveguide_width_um)
    ref6 = c << sbend_bot_out
    ref6.move((bend_length_um + coupling_length_um, bot_y_coupling))

    return c

if __name__ == "__main__":
    c = directional_coupler()
    c.write_gds("experiments/paper_swap/final4/output/recreation_opus45m/device.gds")
    print("GDS written")
