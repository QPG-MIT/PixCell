import gdsfactory as gf
import numpy as np
from gdsfactory.cross_section import Section, cross_section

@gf.cell
def multi_slot_coupler() -> gf.Component:
    c = gf.Component()

    # --- Footprint Constraints & Proportions ---
    # Target footprint width: 120.0 um -> x goes roughly from -60 to 60.
    # Target footprint height: ~4.0 um -> y goes roughly from -2.0 to 2.0.
    
    w_thin = 0.06      # Width of the thin waveguide lines
    gap = 0.06         # Gap size
    pitch = 0.12       # Grating pitch (w_thin + gap)
    W_thick = 1.0      # Width of the thick boundary lines
    x_max = 60.0       # Max half-width
    x_mid_bound = 25.0 # Boundary where the straight section transitions into the flare
    
    # --- 1. Center Group (5 perfectly straight thin lines) ---
    xs_center = cross_section(
        width=w_thin, 
        offset=0, 
        layer=(1, 0),
        sections=[
            Section(width=w_thin, offset=-2*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=-pitch, layer=(1, 0)),
            Section(width=w_thin, offset=pitch, layer=(1, 0)),
            Section(width=w_thin, offset=2*pitch, layer=(1, 0)),
        ]
    )
    
    # Simple straight path spanning from left to right
    path_center = gf.Path([(-x_max, 0), (x_max, 0)])
    c << gf.path.extrude(path_center, cross_section=xs_center)

    # --- 2. Shared Master Path for Top & Bottom Flared Groups ---
    # The 4 thin lines in the top group seamlessly continue the central grating pitch.
    # The center group's highest line is at Y = +0.24.
    # Therefore, the Top group's 4 thin lines must be centered at Y = 0.36, 0.48, 0.60, 0.72.
    y_mid = 0.54  # Center point for the set of the 4 thin lines in the top block
    y_out = 0.75  # The peak Y coordinate of the path at the outer edges (calculated to achieve Y_max ~ 2.0)
    
    n_curve = 200
    
    # Generate coordinates for left and right curved sections exclusively
    x_left = np.linspace(-x_max, -x_mid_bound, n_curve)
    y_left = y_mid + (y_out - y_mid) * (1 - np.cos(((-x_mid_bound - x_left) / (x_max - x_mid_bound)) * np.pi / 2))
        
    x_right = np.linspace(x_mid_bound, x_max, n_curve)
    y_right = y_mid + (y_out - y_mid) * (1 - np.cos(((x_right - x_mid_bound) / (x_max - x_mid_bound)) * np.pi / 2))

    # To eliminate GDS extrusion aliasing/artifacts, avoid dense collinear points in the straight segment.
    # We span the flat middle with precisely two points.
    x_pts = np.concatenate([x_left[:-1], [-x_mid_bound, x_mid_bound], x_right[1:]])
    y_pts = np.concatenate([y_left[:-1], [y_mid, y_mid], y_right[1:]])
    path_flared = gf.Path(list(zip(x_pts, y_pts)))
    
    # --- 3. Cross-Section Definition for Flared Groups ---
    # Offset calculation for the thick bounding block:
    # Topmost thin line is at +0.18 relative to path; its top edge is at +0.21.
    # A gap of 0.06 places the bottom edge of the thick block at +0.27.
    # The center line of the thick block is therefore at +0.27 + (W_thick / 2) = +0.77.
    offset_thick = 0.77
    
    xs_flared = cross_section(
        width=w_thin, 
        offset=-1.5*pitch,  # Reference base layout (lowest thin line)
        layer=(1, 0),
        sections=[
            Section(width=w_thin, offset=-0.5*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=0.5*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=1.5*pitch, layer=(1, 0)),
            Section(width=W_thick, offset=offset_thick, layer=(1, 0)),
        ]
    )

    # --- 4. Assembly ---
    # Extrude and place Top Component
    c << gf.path.extrude(path_flared, cross_section=xs_flared)

    # Extrude and precisely mirror the Bottom Component for perfect symmetry
    bottom_comp = c << gf.path.extrude(path_flared, cross_section=xs_flared)
    bottom_comp.mirror(p1=(0, 0), p2=(1, 0))

    return c

if __name__ == "__main__":
    device = multi_slot_coupler()
    device.show()
    device.write_gds("multi_slot_coupler.gds")