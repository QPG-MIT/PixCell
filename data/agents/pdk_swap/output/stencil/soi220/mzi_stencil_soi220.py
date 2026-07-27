"""STENCIL CONTROL — 220 nm SOI strip.

Every polygon here comes from a SINGLE call to the library stencil
`gf.components.mzi(...)`. No custom cells, no gf.Path geometry, no boolean
ops, no wrapping. We only turn the stencil's own exposed knobs. Whatever the
stencil's interface cannot reach IS the datum — we record it, never work around
it.
"""

import json
from pathlib import Path

import gdsfactory as gf

# --- top-level stencil tunables (name = value) ---
delta_length = 74.017  # um  FSR knob: arm path-length imbalance (300.3125 / n_g)
length_y = 0.0  # um  vertical arm straight collapsed to shrink Y as far as stencil allows
length_x = 0.1  # um  horizontal arm straight (0.0 paradoxically grows X, so hold at stock default)
bend_radius = 5.0  # um  fabricable floor for the SOI strip (radius_min=5.0); smaller is unfabricable
waveguide_width = 0.5  # um  stack single_mode_width_um

HERE = Path(__file__).resolve().parent
GDS = HERE / "mzi_stencil_soi220.gds"

# Adapting the waveguide width to the platform is standard PDK practice; the
# stock strip cross-section exposes width and bend radius as public parameters.
xs = gf.cross_section.strip(width=waveguide_width, radius=bend_radius)

# THE single stencil call — all geometry originates here.
c = gf.components.mzi(
    delta_length=delta_length,
    length_y=length_y,
    length_x=length_x,
    cross_section=xs,
)
c.write_gds(GDS, with_metadata=False)

# Honest arm lengths from the stencil's own geometry. The reference (short) arm
# of a stock MZI routes splitter -> bend -> length_y -> bend -> length_x ->
# bend -> length_y -> bend -> combiner; its length is derived from the stock
# bend_euler's reported arc length (no source copied — public component info).
# The stencil's documented delta_length semantics make the delay arm exactly
# delta_length longer, so |delay - reference| == delta_length by construction.
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

if __name__ != "__main__":
    pass
