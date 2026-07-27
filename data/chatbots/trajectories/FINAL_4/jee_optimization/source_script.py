import numpy as np
import gdsfactory as gf

@gf.cell
def recreate_curved_coupler():
    """
    Recreates the curved waveguide coupler with high visual fidelity.
    Optimized for Turn 4 based on width and gap analysis.
    
    Footprint: 18um x 3um.
    """
    c = gf.Component("curved_coupler_v4")
    
    # 1. Geometry Constraints
    L = 18.0           # Total length (um)
    H = 3.0            # Total height (um)
    w = 0.75           # Thicker waveguide to match the "bold" look of the target
    gap_center = 0.22  # Tight gap at the center for visual accuracy
    resolution = 600   # High point density for perfectly smooth extrusion
    
    # 2. Calculated Vertical Positions (Centerlines)
    # y_outer: waveguide center at the ends (exactly aligned to touch the frame edges)
    y_outer = (H / 2) - (w / 2)
    
    # y_inner: waveguide center at the midpoint (x = L/2)
    y_inner = (gap_center / 2) + (w / 2)
    
    dy = y_outer - y_inner
    
    # 3. Path Generation
    # We use a Quintic Smoothstep for the most organic transition.
    # This ensures zero curvature (flatness) at the ends and the center.
    x_vals = np.linspace(0, L, resolution)
    y_vals_top = []
    
    for x in x_vals:
        t = x / L
        # Normalize x to [0, 1] for each half of the device
        if t <= 0.5:
            # Left half: Transition from Outer down to Inner
            u = t * 2
            # 1 - f(u) transitions 1 -> 0
            f_u = 6*u**5 - 15*u**4 + 10*u**3
            y = y_inner + dy * (1 - f_u)
        else:
            # Right half: Transition from Inner back up to Outer
            u = (t - 0.5) * 2
            # f(u) transitions 0 -> 1
            f_u = 6*u**5 - 15*u**4 + 10*u**3
            y = y_inner + dy * f_u
        y_vals_top.append(y)
    
    # Create Path points for top and bottom (mirrored)
    pts_top = list(zip(x_vals, y_vals_top))
    pts_bot = [(x, -y) for x, y in pts_top]
    
    # 4. Extrusion
    # Use layer (1, 0) as is standard for silicon photonics
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # Generate and add the two waveguide branches
    path_top = gf.Path(pts_top)
    path_bot = gf.Path(pts_bot)
    
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)
    
    # 5. Port definitions (for routing and connectivity check)
    c.add_port("o1", center=(0, y_outer), width=w, orientation=180, layer=(1,0))
    c.add_port("o2", center=(0, -y_outer), width=w, orientation=180, layer=(1,0))
    c.add_port("o3", center=(L, y_outer), width=w, orientation=0, layer=(1,0))
    c.add_port("o4", center=(L, -y_outer), width=w, orientation=0, layer=(1,0))

    return c

if __name__ == "__main__":
    # Instantiate the component
    comp = recreate_curved_coupler()
    
    # Display the component in the GDS viewer (if configured)
    comp.show()
    
    # Export to GDSII
    comp.write_gds("curved_coupler_final.gds")