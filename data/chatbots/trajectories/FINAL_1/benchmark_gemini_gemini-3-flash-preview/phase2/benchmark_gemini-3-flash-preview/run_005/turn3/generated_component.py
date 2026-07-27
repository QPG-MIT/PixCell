import gdsfactory as gf
import numpy as np

@gf.cell(check_instances=False)  # Bypass grid check for the Bezier-based flare
def trident_coupler():
    """
    Trident coupler matching target proportions and footprint.
    Footprint: 40.0 um x 1.7 um.
    Fixed off-grid instance error and attribute error.
    """
    c = gf.Component("trident_coupler")
    
    # --- Dimensions ---
    L_TOTAL = 40.0
    H_TOTAL = 1.7
    layer = (1, 0)
    
    # Waveguide widths
    w_main_start = 0.45
    w_side_in = 0.20   # Side branches start narrow
    w_side_out = 0.48  # Side branches flare to standard width
    gap_in = 0.08      # Narrow gap for strong coupling at the start
    
    # Longitudinal segments
    l_mid_s = 4.0      # Input straight section
    l_mid_t = 28.0     # Central taper ending mid-flare
    
    # Side branches start at the same x as the central taper
    l_side_s1 = 20.0   # Parallel section (side branches stay thin)
    l_side_flare = 10.0 # Flare region (S-bend + widening)
    l_side_s2 = 6.0    # Final output tail
    
    # --- 1. Central Branch ---
    xs_main = gf.cross_section.cross_section(width=w_main_start, layer=layer)
    mid_s = c << gf.components.straight(length=l_mid_s, cross_section=xs_main)
    # Taper down to a fine tip
    mid_t = c << gf.components.taper(length=l_mid_t, width1=w_main_start, width2=0.01, layer=layer)
    mid_t.connect("o1", mid_s.ports["o2"])
    
    # --- 2. Side Branches ---
    # Math to hit 1.7um height: Outer edge must be at y = +/- 0.85
    y_end = (H_TOTAL / 2) - (w_side_out / 2)                # y = 0.61
    y_start = (w_main_start / 2) + gap_in + (w_side_in / 2) # y = 0.405
    dy = y_end - y_start
    
    def add_side_branch(y_sign):
        # A. Initial parallel section (starts at x=4.0)
        xs_in = gf.cross_section.cross_section(width=w_side_in, layer=layer)
        s1 = c << gf.components.straight(length=l_side_s1, cross_section=xs_in)
        s1.move((l_mid_s, y_sign * y_start))
        
        # B. S-Bend Flare with broadening width
        t = np.linspace(0, 1, 100)
        h = y_sign * dy
        l = l_side_flare
        # Cubic Bezier points for a smooth S-bend
        x_pts = (1-t)**3 * 0 + 3*(1-t)**2*t * (l/2) + 3*(1-t)*t**2 * (l/2) + t**3 * l
        y_pts = (1-t)**3 * 0 + 3*(1-t)**2*t * 0 + 3*(1-t)*t**2 * h + t**3 * h
        pts = np.stack([x_pts, y_pts], axis=1)
        
        path = gf.Path(pts)
        
        xs_out = gf.cross_section.cross_section(width=w_side_out, layer=layer)
        trans = gf.path.transition(xs_in, xs_out, width_type='linear')
        
        # Extrude the transition along the Bezier path
        flare = c << gf.path.extrude_transition(path, transition=trans)
        flare.connect("o1", s1.ports["o2"])
        
        # C. Output section
        s2 = c << gf.components.straight(length=l_side_s2, cross_section=xs_out)
        s2.connect("o1", flare.ports["o2"])

    add_side_branch(1)
    add_side_branch(-1)
    
    # Flatten ensures all off-grid instances are merged into polygons 
    # and simplifies the hierarchy for final export.
    return c.flatten()

if __name__ == "__main__":
    device = trident_coupler()
    device.write_gds("trident_coupler.gds")
    
    # Verification printout
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")