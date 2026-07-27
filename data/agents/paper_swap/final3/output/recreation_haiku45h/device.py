"""
Symmetric S-bend directional coupler.
Primitives-only using Path + smooth waypoints.
"""

import gdsfactory as gf
from pathlib import Path as PathlibPath

# Tunable parameters (function-defining knobs at top level)
waveguide_width = 0.44  # Waveguide width in μm
gap_um = 2.0  # Center-to-center gap between guides
bend_radius_um = 20.0  # Bend curvature radius (for reference)
straight_length_um = 40.0  # Center straight section

# Layout
total_length_um = 120.0
y_upper = gap_um / 2
y_lower = -gap_um / 2

@gf.cell
def symmetric_s_bend_coupler():
    """S-bend coupler using gf.path.smooth with waypoints."""
    c = gf.Component()
    layer = (1, 0)

    # Upper waveguide waypoints: Strong S-curve that dips deep toward center
    upper_waypoints = [
        (0, y_upper),               # Inlet
        (26, y_upper - 0.62),       # Start dip (later than before)
        (60, y_upper - 0.91),       # Bottom of dip (deep)
        (94, y_upper - 0.62),       # Rise back up (earlier than before)
        (120, y_upper),             # Outlet
    ]

    # Lower waveguide waypoints: symmetric, opposite direction
    lower_waypoints = [
        (0, y_lower),               # Inlet
        (26, y_lower + 0.62),       # Start rise
        (60, y_lower + 0.91),       # Top of rise (deep)
        (94, y_lower + 0.62),       # Dip back down
        (120, y_lower),             # Outlet
    ]

    # Create paths with smooth waypoints
    upper_path = gf.path.smooth(
        upper_waypoints,
        radius=bend_radius_um,
        npoints=100
    )
    upper_wg = c << gf.path.extrude(upper_path, width=waveguide_width, layer=layer)

    lower_path = gf.path.smooth(
        lower_waypoints,
        radius=bend_radius_um,
        npoints=100
    )
    lower_wg = c << gf.path.extrude(lower_path, width=waveguide_width, layer=layer)

    c.flatten()
    return c


if __name__ == "__main__":
    device = symmetric_s_bend_coupler()
    outdir = PathlibPath(__file__).parent
    outfile = outdir / "device.gds"
    device.write_gds(str(outfile))
    print(f"GDS written to {outfile}")
