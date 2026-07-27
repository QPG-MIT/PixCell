import gdsfactory as gf
import numpy as np

@gf.cell
def recreated_device_geometry():
    """
    Refined recreation of the device geometry (Turn 4).
    Matches the target image more closely in terms of line weights, 
    spacing, and flare curvature profiles.
    
    Footprint: 120.0 x 4.0 um.
    """
    c = gf.Component("recreated_device_v6")
    layer = (1, 0)
    
    # --- Global Constants ---
    W_TOTAL = 120.0
    H_TOTAL = 4.0
    
    # --- 1. CENTRAL GRATING (5 THICK LINES) ---
    # These span the full width of the device with a 50% duty cycle.
    n_center = 5
    center_line_width = 0.12
    center_pitch = 0.24
    
    for i in range(n_center):
        y_pos = (i - (n_center - 1) / 2) * center_pitch
        rect = c << gf.components.rectangle(size=(W_TOTAL, center_line_width), 
                                          layer=layer, centered=True)
        rect.y = y_pos

    # --- 2. TOP & BOTTOM ASSEMBLIES ---
    # Parameters for the flare and layout
    y_start = 0.65    # Height where the top assembly starts
    y_end = 1.95      # Max height for the assembly
    x_base = 49.0     # Half-width at the base of the flare
    x_tip = 59.5      # Half-width at the tips (close to 120um total width)
    flare_p = 2.5     # Curvature power (higher = stays vertical longer near base)
    
    rail_width = 0.05
    rail_gap = 0.25   # Center-to-center spacing of the dual-rail system

    def get_flare_x(y_val):
        """Calculates the x-coordinate for the flare at a given y height."""
        # Normalize y to [0, 1] range relative to the flare section
        t = (abs(y_val) - y_start) / (y_end - y_start)
        t = np.clip(t, 0, 1)
        # Power law transition for the flare curve
        return x_base + (x_tip - x_base) * (t**flare_p)

    def add_half_assembly(is_top=True):
        ys = 1 if is_top else -1
        
        # A. Side Dual-Rails (Curved Outlines)
        # Higher point density (100) for smooth curves in GDS
        rail_xs = gf.cross_section.cross_section(width=rail_width, layer=layer)
        y_pts = np.linspace(y_start, y_end, 100)
        
        # Draw four curved paths: 2 on the left, 2 on the right
        for x_side in [-1, 1]:
            for offset in [-rail_gap/2, rail_gap/2]:
                path_pts = [(x_side * (get_flare_x(y) + offset), y * ys) for y in y_pts]
                c << gf.path.extrude(gf.Path(path_pts), cross_section=rail_xs)
        
        # B. Thick Solid Base Block
        # Fills the region between the inner rail boundaries
        y_block_bot = y_start
        y_block_top = 1.10
        inner_off = -rail_gap/2
        
        block_y_pts = np.linspace(y_block_bot, y_block_top, 40)
        # Right side boundary points
        pts_r = [(get_flare_x(y) + inner_off, y * ys) for y in block_y_pts]
        # Left side boundary points (mirrored and reversed for polygon closure)
        pts_l = [(-x, y) for x, y in reversed(pts_r)]
        
        c.add_polygon(points=pts_r + pts_l, layer=layer)
        
        # C. Thin Horizontal Stripes
        # Bounded by the inner rail boundary at each specific height
        stripe_y_positions = [1.28, 1.46, 1.64, 1.82]
        stripe_height = 0.07
        
        for sy in stripe_y_positions:
            half_w = get_flare_x(sy) + inner_off
            stripe = c << gf.components.rectangle(size=(2 * half_w, stripe_height), 
                                                layer=layer, centered=True)
            stripe.y = sy * ys

    # Generate both top and bottom mirrored halves
    add_half_assembly(is_top=True)
    add_half_assembly(is_top=False)
    
    return c

if __name__ == "__main__":
    # Build the component
    component = recreated_device_geometry()
    
    # Export to GDS file
    component.write_gds("recreated_device_v6.gds")