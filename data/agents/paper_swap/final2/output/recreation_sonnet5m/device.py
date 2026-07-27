"""4-port to 1-port adiabatic waveguide combiner.

Topology: 4 single-mode input waveguides fan in through individual horn
tapers that tile edge-to-edge into a wide multimode transfer block, which
then steps down through a single output taper to one single-mode output
waveguide. Primitives only: straight, taper, rectangle, @gf.cell assembly.
"""

import gdsfactory as gf

LAYER = (1, 0)

# ---- Parametric contract (top-level tunables) ----
wg_width_um = 1.6
num_ports = 4
# Measured port centers are not evenly spaced (symmetric, wider central gap) --
# kept as explicit per-port tunables rather than a single uniform pitch.
port_x_positions_um = [-9.02, -3.48, 3.48, 9.02]
# Per-port taper entry width right where each horn meets the block's flat
# top edge (measured directly from the image at the last row before the
# block's solid full-width span begins) -- horns do NOT touch each other;
# the block itself provides the remaining fill between them.
input_taper_entry_widths_um = [3.13, 3.18, 3.16, 3.27]
input_stem_length_um = 1.8
input_taper_length_um = 1.85
block_width_um = 25.0
block_height_um = 5.05
output_taper_length_um = 1.22
output_taper_entry_width_um = 3.1
output_taper_exit_width_um = 1.6


@gf.cell
def combiner_4to1() -> gf.Component:
    c = gf.Component()

    # y=0 is the bottom tip of the output waveguide; device builds upward.
    y_block_bottom = output_taper_length_um
    y_block_top = y_block_bottom + block_height_um
    y_input_taper_top = y_block_top + input_taper_length_um
    y_top = y_input_taper_top + input_stem_length_um

    # Output taper: narrow (wg_width) at the bottom tip, wide (entry width)
    # at the top where it meets the block's flat bottom edge.
    out_taper = gf.components.taper(
        length=output_taper_length_um,
        width1=output_taper_exit_width_um,
        width2=output_taper_entry_width_um,
        layer=LAYER,
    )
    out_ref = c.add_ref(out_taper)
    out_ref.rotate(90)
    out_ref.move((0 - output_taper_exit_width_um / 2, 0))
    # after rotate+move, re-anchor precisely by bbox center at x=0, ymin=0
    out_ref.x = 0
    out_ref.ymin = 0

    # Central multimode transfer block.
    block = gf.components.rectangle(
        size=(block_width_um, block_height_um), layer=LAYER
    )
    block_ref = c.add_ref(block)
    block_ref.x = 0
    block_ref.ymin = y_block_bottom

    # 4 input ports: each is a taper (wide at the block merge line, narrow
    # at the top) topped with a straight single-mode stem.
    for x, entry_width in zip(port_x_positions_um, input_taper_entry_widths_um):
        in_taper = gf.components.taper(
            length=input_taper_length_um,
            width1=entry_width,
            width2=wg_width_um,
            layer=LAYER,
        )
        in_ref = c.add_ref(in_taper)
        in_ref.rotate(90)
        in_ref.x = x
        in_ref.ymin = y_block_top

        stem = gf.components.straight(
            length=input_stem_length_um,
            cross_section=gf.cross_section.cross_section(layer=LAYER, width=wg_width_um),
        )
        stem_ref = c.add_ref(stem)
        stem_ref.rotate(90)
        stem_ref.x = x
        stem_ref.ymin = y_input_taper_top

    return c


if __name__ == "__main__":
    comp = combiner_4to1()
    gds_path = "component.gds"
    comp.write_gds(gds_path)
    print(f"wrote {gds_path}, bbox={comp.bbox()}")
