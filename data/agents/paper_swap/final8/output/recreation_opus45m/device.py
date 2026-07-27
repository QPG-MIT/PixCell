import gdsfactory as gf
from gdsfactory.typings import LayerSpec
import numpy as np

# === TUNABLES (function-defining knobs) ===
corner_block_length = 22.0
corner_block_width = 1.6
num_waveguides = 5
waveguide_width = 0.055
waveguide_pitch = 0.135
sbend_length = 18.0
structure_gap = 0.35

# === FIXED ===
layer: LayerSpec = (1, 0)
total_length = 120.0


@gf.cell
def single_structure() -> gf.Component:
    """One half: corner blocks with S-bend fanout to parallel waveguides."""
    c = gf.Component()

    # Calculate waveguide positions
    wg_positions = [(i - (num_waveguides - 1) / 2) * waveguide_pitch for i in range(num_waveguides)]

    # Center waveguides span the full length
    for wg_y in wg_positions:
        wg = c << gf.components.rectangle(
            size=(total_length, waveguide_width), layer=layer
        )
        wg.xmin = 0
        wg.y = wg_y

    # Left corner block (large filled region)
    left_block = c << gf.components.rectangle(
        size=(corner_block_length, corner_block_width), layer=layer
    )
    left_block.xmin = 0
    left_block.ymin = -corner_block_width / 2

    # Right corner block
    right_block = c << gf.components.rectangle(
        size=(corner_block_length, corner_block_width), layer=layer
    )
    right_block.xmax = total_length
    right_block.ymin = -corner_block_width / 2

    # Left S-bend tapers - connect corner block to waveguides
    corner_edge_positions = [(i - (num_waveguides - 1) / 2) * (corner_block_width * 0.7 / (num_waveguides - 1)) for i in range(num_waveguides)]

    for corner_y, wg_y in zip(corner_edge_positions, wg_positions):
        npoints = 50
        x = np.linspace(0, sbend_length, npoints)
        y = corner_y + (wg_y - corner_y) * (1 - np.cos(np.pi * x / sbend_length)) / 2

        path = gf.Path(np.column_stack([x, y]))

        taper_w_start = corner_block_width / (num_waveguides + 0.3)
        xs = gf.CrossSection(
            sections=[
                gf.Section(
                    width=taper_w_start,
                    layer=layer,
                    width_function=lambda t, ws=taper_w_start, we=waveguide_width: ws + (we - ws) * t,
                )
            ]
        )

        taper = c << gf.path.extrude(path, xs)
        taper.xmin = corner_block_length

    # Right S-bend tapers
    for corner_y, wg_y in zip(corner_edge_positions, wg_positions):
        npoints = 50
        x = np.linspace(0, sbend_length, npoints)
        y = wg_y + (corner_y - wg_y) * (1 - np.cos(np.pi * x / sbend_length)) / 2

        path = gf.Path(np.column_stack([x, y]))

        taper_w_end = corner_block_width / (num_waveguides + 0.3)
        xs = gf.CrossSection(
            sections=[
                gf.Section(
                    width=waveguide_width,
                    layer=layer,
                    width_function=lambda t, ws=waveguide_width, we=taper_w_end: ws + (we - ws) * t,
                )
            ]
        )

        taper = c << gf.path.extrude(path, xs)
        taper.xmin = total_length - corner_block_length - sbend_length

    return c


@gf.cell
def dual_structure_device() -> gf.Component:
    """Two structures stacked vertically."""
    c = gf.Component()

    # Top structure
    top = c << single_structure()
    top.ymin = structure_gap / 2

    # Bottom structure (mirrored vertically)
    bottom = c << single_structure()
    bottom.mirror_y()
    bottom.ymax = -structure_gap / 2

    # Center horizontally
    c.move((-total_length / 2, 0))

    return c


if __name__ == "__main__":
    c = dual_structure_device()
    c.write_gds("experiments/paper_swap/final8/output/recreation_opus45m/device.gds")
    print(f"Device size: {c.xsize:.2f} x {c.ysize:.2f} um")
