import gdsfactory as gf
import numpy as np

@gf.cell
def device_parametric():
    """
    Constructs a multi-waveguide directional coupler with adiabatic outer structures.
    
    The device consists of:
    1. A central bundle of 5 straight waveguides.
    2. Outer adiabatic blocks that flank the central bundle. These blocks have a straight
       inner edge facing the bundle and a curved outer edge (cosine taper).
    3. The outer blocks have longitudinal slots cut into them near the inner edge,
       creating the appearance of waveguides merging into the bulk material ("rails").
       
    The geometry is tuned to fit a tight footprint of 120um x 4um while retaining
    the specific visual features of the target image.
    """
    c = gf.Component()

    # --- Dimensions & Parameters ---
    length = 120.0
    
    # Waveguide dimensions (tuned for compact 4um height)
    w_wg = 0.15          # Waveguide width
    g_wg = 0.15          # Gap between waveguides
    pitch = w_wg + g_wg
    
    layer_wg = (1, 0)
    xs_wg = gf.cross_section.cross_section(width=w_wg, layer=layer_wg)

    # --- 1. Central Waveguide Bundle ---
    # 5 straight waveguides centered at y=0.
    # Indices: -2, -1, 0, 1, 2
    n_center = 5
    for i in range(-(n_center // 2), (n_center // 2) + 1):
        wg = c << gf.components.straight(length=length, cross_section=xs_wg)
        wg.movey(i * pitch)
    
    # Calculate the Y-coordinate of the top edge of the central bundle
    # Center y=0. Top waveguide is at y = 2*pitch. Its top edge is at 2*pitch + w/2.
    y_center_top_edge = (n_center // 2) * pitch + w_wg / 2

    # --- 2. Outer Adiabatic Blocks ---
    # The blocks start after a small gap from the central bundle.
    g_sep = 0.2
    y_block_inner = y_center_top_edge + g_sep

    # Function to create the custom slotted block geometry
    def create_slotted_block():
        """
        Creates a solid block with a cosine-tapered outer edge and internal longitudinal slots.
        Local Coordinates:
        - y=0 corresponds to the straight inner edge of the block.
        - y increases towards the outer edge.
        """
        # Parameters for the slots (rails)
        # We create 2 slots, which defines 2 "rails" before the solid bulk.
        # Rail 0 (0 to w), Slot 0 (w to w+g), Rail 1 (w+g to 2w+g), Slot 1 (2w+g to 2w+2g)
        num_slots = 2
        y_slots_end = num_slots * (w_wg + g_wg)
        
        # Block Width Profile (Inner edge to Outer edge)
        # w_min: Width at the center of the device (narrowest).
        # Must be large enough to contain the slots/rails.
        w_min = y_slots_end + 0.15 
        
        # w_max: Width at the ends of the device (widest).
        # Controls the curvature "flare".
        w_max = y_slots_end + 0.6
        
        # A. Create Solid Tapered Body
        # Generate points for the outer curve
        num_pts = 501
        x = np.linspace(0, length, num_pts)
        
        # Cosine Taper: 1 at ends, 0 at center
        # width(x) = w_min + (w_max - w_min) * 0.5 * (1 + cos(2*pi*x/L))
        factor = 0.5 * (1 + np.cos(2 * np.pi * x / length))
        w_profile = w_min + (w_max - w_min) * factor
        
        # Vertices for polygon
        # Top edge: (x, w_profile)
        # Bottom edge: (x, 0) -> Straight inner line
        pts_top = np.stack((x, w_profile), axis=1)
        pts_bot = np.stack((x[::-1], np.zeros_like(x)), axis=1) # Reverse x for proper winding
        pts = np.concatenate((pts_top, pts_bot))
        
        solid = gf.Component()
        solid.add_polygon(pts, layer=layer_wg)
        
        # B. Create Slots to Subtract
        slots = gf.Component()
        for i in range(num_slots):
            # Calculate slot position
            # Slot 0 starts after Rail 0 (width w_wg)
            # Slot 1 starts after Rail 0 + Slot 0 + Rail 1
            y_start = (i + 1) * w_wg + i * g_wg
            y_center = y_start + g_wg / 2
            
            # Create slot rectangle
            s = slots << gf.components.rectangle(size=(length, g_wg), layer=layer_wg, centered=True)
            s.move((length / 2, y_center))
            
        # C. Boolean Operation (Solid MINUS Slots)
        return gf.boolean(solid, slots, operation="not", layer=layer_wg)

    # Instantiate the block component
    block = create_slotted_block()
    
    # Place Top Block
    # The block's y=0 is placed at y_block_inner
    top_ref = c << block
    top_ref.movey(y_block_inner)
    
    # Place Bottom Block
    # Mirror vertically, then move to position
    bot_ref = c << block
    bot_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
    bot_ref.movey(-y_block_inner)      # Move inner edge to correct separation
    
    # --- 3. Ports ---
    # Add optical ports at the ends of the central waveguide
    c.add_port("o1", center=(0, 0), width=w_wg, orientation=180, layer=layer_wg)
    c.add_port("o2", center=(length, 0), width=w_wg, orientation=0, layer=layer_wg)

    return c

if __name__ == "__main__":
    component = device_parametric()
    component.write_gds("parametric_coupler.gds")