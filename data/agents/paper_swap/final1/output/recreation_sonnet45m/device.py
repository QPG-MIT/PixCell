import gdsfactory as gf
import numpy as np

# Tunables - function-defining knobs
input_width = 0.55
coupling_gap = 0.2
narrow_width = 0.45
taper_length = 8.0
coupling_length = 24.0
total_height = 1.7

layer = (1, 0)

@gf.cell
def directional_coupler():
    c = gf.Component()

    # Position guides with the coupling gap in mind
    # Total occupied = narrow_width + coupling_gap + narrow_width at coupling region
    input_gap = 0.25  # gap between guide edges at input

    y_top = input_gap / 2 + input_width / 2
    y_bottom = -(input_gap / 2 + input_width / 2)

    # Top waveguide - three sections
    # Input taper
    top_taper1 = gf.components.taper(
        length=taper_length,
        width1=input_width,
        width2=narrow_width,
        layer=layer
    )
    t1 = c << top_taper1
    t1.dmove((0, y_top))

    # Coupling section
    top_straight = gf.components.rectangle(
        size=(coupling_length, narrow_width),
        layer=layer,
        centered=True
    )
    ts = c << top_straight
    ts.dmove((taper_length + coupling_length/2, y_top))

    # Output taper
    top_taper2 = gf.components.taper(
        length=taper_length,
        width1=narrow_width,
        width2=input_width,
        layer=layer
    )
    t2 = c << top_taper2
    t2.dmove((taper_length + coupling_length, y_top))

    # Bottom waveguide - three sections
    # Input taper
    bottom_taper1 = gf.components.taper(
        length=taper_length,
        width1=input_width,
        width2=narrow_width,
        layer=layer
    )
    b1 = c << bottom_taper1
    b1.dmove((0, y_bottom))

    # Coupling section
    bottom_straight = gf.components.rectangle(
        size=(coupling_length, narrow_width),
        layer=layer,
        centered=True
    )
    bs = c << bottom_straight
    bs.dmove((taper_length + coupling_length/2, y_bottom))

    # Output taper
    bottom_taper2 = gf.components.taper(
        length=taper_length,
        width1=narrow_width,
        width2=input_width,
        layer=layer
    )
    b2 = c << bottom_taper2
    b2.dmove((taper_length + coupling_length, y_bottom))

    return c

if __name__ == "__main__":
    import os
    from pathlib import Path
    device = directional_coupler()
    # Write to the same directory as this script
    script_dir = Path(__file__).parent
    outpath = script_dir / "device.gds"
    if outpath.exists():
        outpath.unlink()
    device.write_gds(str(outpath))
    print(f"Wrote {outpath}")
