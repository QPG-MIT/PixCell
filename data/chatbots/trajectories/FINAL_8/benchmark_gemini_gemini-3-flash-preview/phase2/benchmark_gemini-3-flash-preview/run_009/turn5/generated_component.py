import gdsfactory as gf
import numpy as np

def create_concave_pts(L, y_mid, y_ends, n=200):
    """
    Generates points for a concave curve (parabolic) where the 
    lowest point is at the center (x=0).
    """
    x = np.linspace(-L/2, L/2, n)
    # y = a*x^2 + c
    # at x=0, y=y_mid => c = y_mid
    # at x=L/2, y=y_ends => a = (y_ends - y_mid) / (L/2)**2
    a = (y_ends - y_mid) / (L/2)**2
    y = a * x**2 + y_mid
    return list(zip(x, y))

@gf.cell
def matched_photonic_device_v5_fixed():
    """
    Turn 5 Corrected:
    - Fixes the DBU validation error by using even-numbered widths (0.04um).
    - Matches the 'pinched' look: arms are thinnest at the center.
    - Inner edge of arms is flat to create a uniform channel.
    - Outer edge and satellite lines follow a concave arc.
    """
    c = gf.Component("pinched_device_v5")
    layer = (1, 0)
    L = 120.0
    
    # Use widths that are even multiples of typical DBU (1nm) to avoid symmetry errors
    w_thin = 0.04 
    g_thin = 0.06
    
    # 1. Central Bus (5 straight lines)
    xs_bus = gf.cross_section.cross_section(width=w_thin, layer=layer)
    for i in range(5):
        y_off = (i - 2) * (w_thin + g_thin)
        line = c << gf.components.straight(length=L, cross_section=xs_bus)
        line.center = (0, y_off)

    # 2. Top and Bottom Symmetric Arms
    y_gap_to_bus = 0.60   # Vertical space between bus and arm
    y_slab_inner = y_gap_to_bus
    y_slab_outer_mid = 0.85  # Slab is thin here
    y_slab_outer_end = 1.70  # Slab is thick here
    
    def build_arm(is_bottom=False):
        arm_comp = gf.Component()
        
        # Outer boundary of the slab (Concave)
        pts_outer = create_concave_pts(L, y_slab_outer_mid, y_slab_outer_end)
        
        # Slab Polygon (Concave top, Flat bottom)
        # We close the loop by going to the corners of the flat inner edge
        slab_poly = pts_outer + [(L/2, y_slab_inner), (-L/2, y_slab_inner)]
        arm_comp.add_polygon(slab_poly, layer=layer)
        
        # 3. Outer Satellite Lines (5 lines following the concave curve)
        xs_sat = gf.cross_section.cross_section(width=w_thin, layer=layer)
        for i in range(5):
            # Offset each line from the slab's outer boundary
            offset = 0.10 + i * (w_thin + g_thin)
            pts_shifted = [(x, y + offset) for x, y in pts_outer]
            # Convert points to a Path and extrude
            path = gf.Path(pts_shifted)
            arm_comp << gf.path.extrude(path, cross_section=xs_sat)
            
        # Add arm to main component with mirroring for bottom
        ref = c << arm_comp
        if is_bottom:
            ref.mirror(p1=(0, 0), p2=(1, 0))

    build_arm(is_bottom=False)
    build_arm(is_bottom=True)

    # 4. Vertical Termination Lines (End caps)
    # Very thin vertical lines at the far left and right edges
    for x_pos in [-L/2, L/2]:
        v_line = c << gf.components.rectangle(size=(0.04, 4.0), layer=layer)
        v_line.center = (x_pos, 0)

    # Center the component
    c.x = 0
    c.y = 0
    
    return c

if __name__ == "__main__":
    component = matched_photonic_device_v5_fixed()
    component.write_gds("matched_photonic_device_v5_fixed.gds")