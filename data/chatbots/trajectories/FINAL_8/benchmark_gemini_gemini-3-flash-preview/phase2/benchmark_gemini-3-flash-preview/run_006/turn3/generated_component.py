import gdsfactory as gf
import numpy as np

@gf.cell
def recreated_device_geometry():
    """
    Recreates the device geometry with a focus on smooth integration and correct API usage.
    Fixes the 'locked cell' and 'module has no attribute polygon' errors.
    Footprint: 120.0 x 4.0 um.
    """
    c = gf.Component("recreated_device_v5")
    layer = (1, 0)
    
    # --- Dimensions & Constraints ---
    W_MAX = 120.0  # Width of central lines
    H_MAX = 4.0
    
    # Vertical spacing parameters
    center_pitch = 0.20
    y_block_start = 0.60   # Start of the top/bottom assemblies
    y_block_end = 1.90     # End of the assembly (within 2.0um half-height)
    
    # Flare Curve Parameters (Quadratic Bezier)
    # Defines the x-path of the outer rail center
    x_start = 42.0  # Half-width at the base of the block
    x_mid = 44.0    # Control point for curvature
    x_end = 56.0    # Half-width at the flared tips
    rail_gap = 0.35 # Spacing between dual-rail centers
    rail_width = 0.08

    def get_rail_x(y_abs, x_offset=0):
        """Calculates the x-coordinate of a rail at a given absolute y height."""
        # Normalize y to [0, 1] range for the flare section
        t = (y_abs - y_block_start) / (y_block_end - y_block_start)
        t = np.clip(t, 0, 1)
        # Quadratic Bezier: (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
        x_base = (1 - t)**2 * x_start + 2 * (1 - t) * t * x_mid + t**2 * x_end
        return x_base + x_offset

    # 1. CENTRAL GRATING (5 Full-Width Lines)
    n_center = 5
    center_w = 0.07
    for i in range(n_center):
        y_pos = (i - (n_center - 1) / 2) * center_pitch
        # Create reference first, then transform
        rect_ref = c << gf.components.rectangle(size=(W_MAX, center_w), layer=layer, centered=True)
        rect_ref.y = y_pos

    # 2. TOP AND BOTTOM SYMMETRIC ASSEMBLIES
    def add_assembly(is_top=True):
        ys = 1 if is_top else -1
        
        # A. Solid Thick Base Block
        # Fills the region between the inner rails from start height to a specific end height
        y_thick_top = 1.15
        inner_off = -rail_gap / 2
        
        y_steps = np.linspace(y_block_start, y_thick_top, 15)
        # Right side boundary points
        pts_r = [(get_rail_x(y, inner_off), y * ys) for y in y_steps]
        # Left side boundary points (mirrored)
        pts_l = [(-x, y) for x, y in reversed(pts_r)]
        
        # add_polygon is the robust way to add arbitrary shapes
        c.add_polygon(points=pts_r + pts_l, layer=layer)
        
        # B. Thin Horizontal Bars (Integrated with Rails)
        n_thin = 4
        thin_pitch = 0.18
        thin_w = 0.06
        bar_start_y = 1.35
        for i in range(n_thin):
            curr_y = bar_start_y + (i * thin_pitch)
            # Width is determined by the inner rail position at this specific height
            half_w = get_rail_x(curr_y, inner_off)
            bar_ref = c << gf.components.rectangle(size=(2 * half_w, thin_w), layer=layer, centered=True)
            bar_ref.y = curr_y * ys
            
        # C. Side Curved Dual-Rails
        rail_xs = gf.cross_section.cross_section(width=rail_width, layer=layer)
        path_y_pts = np.linspace(y_block_start, y_block_end, 30)
        
        # Offsets for the dual-rail system (Outer and Inner)
        offsets = [rail_gap / 2, -rail_gap / 2]
        for x_sign in [-1, 1]:
            for off in offsets:
                pts = [(x_sign * get_rail_x(y, off), y * ys) for y in path_y_pts]
                # Using gf.Path and extrude to create the curved lines
                c << gf.path.extrude(gf.Path(pts), cross_section=rail_xs)

    # Generate both top and bottom halves
    add_assembly(is_top=True)
    add_assembly(is_top=False)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = recreated_device_geometry()
    
    # Save the geometry to a GDS file
    component.write_gds("recreated_device_v5.gds")