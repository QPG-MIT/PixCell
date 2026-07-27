import numpy as np
import gdsfactory as gf

@gf.cell
def recreate_curved_coupler():
    """
    Recreates the curved waveguide coupler with high visual fidelity for Turn 5.
    
    Features:
    - Variable width (tapering) from ports to the coupling center.
    - Quintic interpolation for smooth, adiabatic-like curvature transitions.
    - Precise vertical alignment to utilize the full 3um height.
    
    Footprint: 18um x 3um.
    """
    c = gf.Component("curved_coupler_v5")
    
    # 1. Geometry Constraints (um)
    L = 18.0
    H = 3.0
    
    # 2. Parametric Tuning
    # Waveguide is thickest at the ends and thinnest in the middle.
    w_end = 1.05      # Large width at ports to match target "boldness"
    w_mid = 0.42      # Thinner width in the coupling region
    gap_mid = 0.12    # Very tight gap at the center
    
    # 3. Position Calculations
    # Centerline at ends: positioned so outer edge is at H/2 (1.5um)
    y_end = (H / 2) - (w_end / 2) 
    # Centerline at middle: based on gap and local width
    y_mid = (gap_mid / 2) + (w_mid / 2)
    
    # 4. Point Generation
    resolution = 500  # High density for smooth edges
    x_vals = np.linspace(0, L, resolution)
    
    # Smoothstep function for zero-curvature ends (6t^5 - 15t^4 + 10t^3)
    def smoothstep(t):
        return 6*t**5 - 15*t**4 + 10*t**3

    y_centers = []
    widths = []
    
    for x in x_vals:
        # Normalize x to [0, 1] relative to the nearest end (0=end, 1=center)
        t = (2 * x / L) if x <= L/2 else (2 * (L - x) / L)
        s = smoothstep(t)
        
        # Linearly interpolate centerline and width based on the smoothstep factor
        yc = y_end + (y_mid - y_end) * s
        w = w_end + (w_mid - w_end) * s
        
        y_centers.append(yc)
        widths.append(w)
    
    # 5. Polygon Construction
    # We construct the branches by defining the top and bottom edges of each waveguide
    
    # Top Branch
    top_branch_upper = [(x, yc + w/2) for x, yc, w in zip(x_vals, y_centers, widths)]
    top_branch_lower = [(x, yc - w/2) for x, yc, w in zip(x_vals, y_centers, widths)]
    c.add_polygon(top_branch_upper + top_branch_lower[::-1], layer=(1, 0))
    
    # Bottom Branch (mirrored across y=0)
    bot_branch_upper = [(x, -yc + w/2) for x, yc, w in zip(x_vals, y_centers, widths)]
    bot_branch_lower = [(x, -yc - w/2) for x, yc, w in zip(x_vals, y_centers, widths)]
    c.add_polygon(bot_branch_upper + bot_branch_lower[::-1], layer=(1, 0))
    
    # 6. Port definitions (Industry Standard)
    c.add_port("o1", center=(0, y_end), width=w_end, orientation=180, layer=(1,0))
    c.add_port("o2", center=(0, -y_end), width=w_end, orientation=180, layer=(1,0))
    c.add_port("o3", center=(L, y_end), width=w_end, orientation=0, layer=(1,0))
    c.add_port("o4", center=(L, -y_end), width=w_end, orientation=0, layer=(1,0))

    return c

if __name__ == "__main__":
    # Create the component
    comp = recreate_curved_coupler()
    
    # Export to GDSII
    comp.write_gds("curved_coupler_v5.gds")
    
    # Show in local viewer if available
    comp.show()