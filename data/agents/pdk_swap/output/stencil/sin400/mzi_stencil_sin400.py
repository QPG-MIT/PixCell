"""STENCIL CONTROL — 400 nm SiN strip.

All geometry from a SINGLE call to `gf.components.mzi(...)`. Only stock knobs
are turned. Adapting the guide width to the platform (1.0 um) is standard PDK
practice, done through the stock strip cross-section; the stock mmi1x2 splitter
is width-matched via the same cross-section (configuring a stock factory, not a
new cell). Whatever the interface cannot reach is recorded, never worked around.
"""

import json
import warnings
from functools import partial
from pathlib import Path

import gdsfactory as gf

# --- top-level stencil tunables (name = value) ---
delta_length = 148.574  # um  FSR knob: arm imbalance (300.3125 / n_g, n_g=2.0213)
length_y = 0.0  # um  vertical arm collapsed to shrink Y as far as the stencil allows
length_x = 0.1  # um  horizontal arm straight (stock default)
bend_radius = 5.0  # um  compact fabricable floor (smaller trips strip radius_min)
waveguide_width = 1.0  # um  stack single_mode_width_um

HERE = Path(__file__).resolve().parent
GDS = HERE / "mzi_stencil_sin400.gds"

# The wider SiN guide forces the stock mmi1x2's taper to the guide width (the
# factory warns it drops width_mmi) — a stencil-interface artifact we accept:
# the port widths match and every polygon still comes from the one mzi call.
xs = gf.cross_section.strip(width=waveguide_width, radius=bend_radius)
splitter = partial(gf.components.mmi1x2, cross_section=xs)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    c = gf.components.mzi(
        delta_length=delta_length,
        length_y=length_y,
        length_x=length_x,
        cross_section=xs,
        splitter=splitter,
    )
    c.write_gds(GDS, with_metadata=False)

# Honest arm lengths from the stencil's own geometry (see soi220 note).
bend_arc = float(gf.components.bend_euler(cross_section=xs).info["length"])
reference_arm = length_x + 2.0 * length_y + 4.0 * bend_arc
delay_arm = reference_arm + delta_length

(HERE / "lengths.json").write_text(
    json.dumps(
        {
            "arms": {
                "reference_arm_um": reference_arm,
                "delay_arm_um": delay_arm,
            },
            "delta_length_um": delta_length,
        },
        indent=2,
    )
)
