import gdsfactory as gf
import numpy as np

def create_bezier_points(p0, p1, p2, p3, n=200):
    """Generates points for a cubic Bezier curve."""
    t = np.linspace(0, 1, n)
    # P(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    pts = (1-t)**3 * np.array(p0)[:,None] + \
          3*(1-t)**2 * t * np.array(p1)[:,None] + \
          3*(1-t) * t**2 * np.array(p2)[:,None] + \
          t**3 * np.array(p3)[:,None]
    return list(zip(pts[0], pts[1]))

@gf.cell
def improved_photonic_taper():
    """
    Matched version for Turn 3.
    Recreates the smooth pinched geometry using manual Bezier point generation.
    Footprint: 120um x 4um
    """
    c = gf.Component("smooth_pinched_device")
    
    # Geometric Parameters
    length = 120.0
    layer = (1, 0)
    w_line = 0.05      # Width of waveguides
    g_line = 0.05      # Gap between waveguides
    w_slab = 0.7       # Solid slab width
    g_slab_rail = 0.06 # Gap between slab and outer line group
    
    # 1. Central Horizontal Group (5 lines)
    xs_line = gf.cross_section.cross_section(width=w_line, layer=layer)
    for i in range(5):
        y_offset = (i - 2) * (w_line + g_line)
        line = c << gf.components.straight(length=length, cross_section=xs_line)
        line.center = (0, y_offset)

    # 2. Construct the Curved Path
    # Using two Bezier segments (left half and right half) for a symmetric "horn"
    y_pinch = 0.82   # Center of slab at the tightest point
    y_flare = 1.35   # Center of slab at the ends
    x_mid = 15.0     # Horizontal extent of the flat pinch region
    
    # Left Half Control Points (from flare to pinch)
    p0 = (-length/2, y_flare)
    p1 = (-length/4, y_flare)
    p2 = (-x_mid, y_pinch)
    p3 = (0, y_pinch)
    left_pts = create_bezier_points(p0, p1, p2, p3)
    
    # Right Half (Mirroring left points horizontally)
    right_pts = [( -x, y ) for x, y in reversed(left_pts)]
    all_pts = left_pts + right_pts[1:] # Combine and remove duplicate center point
    
    full_path = gf.Path(all_pts)

    # 3. Component Arm Assembly (Slab + Satellite Lines)
    @gf.cell
    def make_horn_arm():
        hc = gf.Component()
        # Add the thick slab
        xs_slab = gf.cross_section.cross_section(width=w_slab, layer=layer)
        hc << gf.path.extrude(full_path, cross_section=xs_slab)
        
        # Add the 5 thin waveguides following the slab's outer curvature
        for i in range(5):
            # Calculate distance from the center of the path to the line's center
            # offset = half_slab + gap + half_line + (index * total_line_step)
            offset = (w_slab / 2) + g_slab_rail + (w_line / 2) + i * (w_line + g_line)
            line_ref = hc << gf.path.extrude(full_path, cross_section=xs_line)
            line_ref.movey(offset)
        return hc

    # Add Top Arm
    top_arm = c << make_horn_arm()
    
    # Add Bottom Arm (Mirrored Top Arm)
    bottom_arm = c << make_horn_arm()
    bottom_arm.mirror(p1=(0, 0), p2=(1, 0))
    
    # Center the entire device
    c.x = 0
    c.y = 0
    
    return c

if __name__ == "__main__":
    # Create and save the component
    component = improved_photonic_taper()
    component.write_gds("improved_photonic_device_v3.gds")