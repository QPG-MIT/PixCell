import gdsfactory as gf
import numpy as np
from gdsfactory.cross_section import Section, cross_section

@gf.cell
def multi_slot_coupler() -> gf.Component:
    c = gf.Component()

    # --- Footprint & Proportions Constraint ---
    # Width = 120.0, target footprint height ~ 4.0 (Y goes roughly from -2.0 to 2.0)
    w_thin = 0.06      # Width of the thin waveguide lines
    pitch = 0.12       # Grating pitch (width 0.06 + gap 0.06)
    W_thick = 0.8      # Width of the massive outer boundary lines
    x_mid_bound = 25.0 # The x-coordinate where the straight section ends and flare begins
    x_max = 60.0       # Max half-width
    
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
    
    path_center = gf.Path([(-x_max, 0), (x_max, 0)])
    c << gf.path.extrude(path_center, cross_section=xs_center)

    # --- 2. Top Flared Group ---
    # The 4 thin lines in the top group must seamlessly continue the central grating pitch.
    # Center group's highest line is at Y = +0.24.
    # Therefore, Top group's thin lines must be at Y = 0.36, 0.48, 0.60, 0.72.
    # The master path for the top group will be centered at the average of these 4 lines:
    y_mid = 0.54
    
    # Outer Y coordinate target for the path at x_max
    y_out = 0.90 
    
    n_pts = 100
    
    # Left flare: half-cosine to maintain non-zero slope at boundary
    x_left = np.linspace(-x_max, -x_mid_bound, n_pts)
    t_left = (-x_mid_bound - x_left) / (x_max - x_mid_bound)
    y_left = y_mid + (y_out - y_mid) * (1 - np.cos(t_left * np.pi / 2))
    
    # Middle perfectly straight section
    x_mid = np.linspace(-x_mid_bound, x_mid_bound, 10)
    y_mid_arr = np.full_like(x_mid, y_mid)
    
    # Right flare: half-cosine
    x_right = np.linspace(x_mid_bound, x_max, n_pts)
    t_right = (x_right - x_mid_bound) / (x_max - x_mid_bound)
    y_right = y_mid + (y_out - y_mid) * (1 - np.cos(t_right * np.pi / 2))
    
    # Combine path arrays safely
    x_pts = np.concatenate([x_left, x_mid[1:-1], x_right])
    y_pts = np.concatenate([y_left, y_mid_arr[1:-1], y_right])
    path_top = gf.Path(list(zip(x_pts, y_pts)))
    
    # Offset calculation for the thick outer line
    # Highest thin line in this group is at +1.5*pitch (+0.18) relative to path.
    # Top edge of that thin line is +0.18 + w_thin/2 = +0.21.
    # Enforcing an exact matching gap of 0.06 places the thick line's bottom at +0.27.
    # Center of thick line is then +0.27 + (W_thick / 2) = +0.67 relative to the path.
    offset_thick = 0.67
    
    xs_top = cross_section(
        width=w_thin, 
        offset=-1.5*pitch,  # Reference base width
        layer=(1, 0),
        sections=[
            Section(width=w_thin, offset=-0.5*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=0.5*pitch, layer=(1, 0)),
            Section(width=w_thin, offset=1.5*pitch, layer=(1, 0)),
            Section(width=W_thick, offset=offset_thick, layer=(1, 0)),
        ]
    )

    # Extrude Top component from master path
    top_comp = c << gf.path.extrude(path_top, cross_section=xs_top)

    # --- 3. Bottom Flared Group ---
    # Due to perfect symmetry, simply duplicate the top component and mirror it across the X-axis
    bottom_comp = c << gf.path.extrude(path_top, cross_section=xs_top)
    bottom_comp.mirror(p1=(0, 0), p2=(1, 0))

    return c

if __name__ == "__main__":
    device = multi_slot_coupler()
    device.show()
    device.write_gds("multi_slot_coupler.gds")