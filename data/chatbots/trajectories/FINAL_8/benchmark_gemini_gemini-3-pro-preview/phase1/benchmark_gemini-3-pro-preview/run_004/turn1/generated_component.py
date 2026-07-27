import gdsfactory as gf
import numpy as np

@gf.cell
def device_120_4():
    """
    Recreates the coupled waveguide device with central straight section
    and outer tapered/curved blocks.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # ==========================================
    # Parameters & Dimensions
    # ==========================================
    # Geometric constraints
    L_inner = 100.0       # Length of the straight inner edge (and center lines)
    L_outer = 120.0       # Maximum length at the outer edge
    H_total = 4.0         # Total height budget
    
    # Layer definition
    layer = (1, 0)
    
    # Center Grating Parameters
    n_center = 5          # Number of center lines
    w_center = 0.15       # Width of center lines
    g_center = 0.1        # Gap between center lines
    
    # Calculate vertical spacing
    # Height occupied by center bundle
    h_center_bundle = n_center * w_center + (n_center - 1) * g_center
    
    # Height of gaps separating center from outer blocks
    gap_main = 0.3
    
    # Height remaining for the two outer blocks
    # H_total = h_center_bundle + 2*gap_main + 2*h_block
    h_block = (H_total - h_center_bundle - 2 * gap_main) / 2
    # This should be approx 1.125um
    
    # ==========================================
    # 1. Center Component: Straight Grating
    # ==========================================
    # A group of 5 parallel rectangles
    center_comp = gf.Component()
    y_start_center = -h_center_bundle / 2 + w_center / 2
    
    for i in range(n_center):
        y = y_start_center + i * (w_center + g_center)
        # Using parametric rectangle
        rect = center_comp << gf.components.rectangle(size=(L_inner, w_center), layer=layer, centered=True)
        rect.movey(y)
        
    c << center_comp

    # ==========================================
    # 2. Outer Block Component (Tapered Horn)
    # ==========================================
    # We construct the curved "horn" shape using a path transition extruded along a path.
    # The width of the extrusion varies from L_inner to L_outer.
    # Since path extrusions define width perpendicular to the path, we create a 
    # vertical extrusion (path along Y) by making a horizontal one and rotating it.
    
    # Define Cross Sections for the transition
    xs_narrow = gf.cross_section.cross_section(width=L_inner, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=L_outer, layer=layer)
    
    # Create the transition with a sine profile for smooth curvature
    # This mimics the "Euler" or smooth bend look of the outer edges
    trans = gf.path.transition(xs_narrow, xs_wide, width_type='sine')
    
    # Define the path length corresponding to the block height
    p = gf.path.straight(length=h_block)
    
    # Extrude the transition
    horn_ref = gf.path.extrude_transition(p, trans)
    
    # Create a container component for the block to perform boolean operations (slots)
    block_base = gf.Component()
    horn = block_base << horn_ref
    # Rotate 90 degrees so the "width" (L_inner to L_outer) aligns with X
    # and the "length" (h_block) aligns with Y.
    horn.rotate(90)
    
    # Create Slots (White lines inside the block)
    # These are horizontal cuts.
    slots = gf.Component()
    slot_width = L_outer + 10.0 # Ensure it cuts through fully
    slot_height = g_center
    
    # Position slots relative to the inner edge (bottom of the rotated block)
    # The rotated block occupies Y from 0 to h_block
    slot_y_positions = [0.25, 0.55] 
    
    for y_s in slot_y_positions:
        s = slots << gf.components.rectangle(size=(slot_width, slot_height), layer=layer, centered=True)
        s.movey(y_s)
        
    # Apply Boolean subtraction: Block - Slots
    final_block = gf.boolean(block_base, slots, operation='not', layer=layer)
    
    # ==========================================
    # 3. Assembly
    # ==========================================
    
    # Calculate placement Y coordinate
    # The block sits above the main gap
    y_placement = h_center_bundle / 2 + gap_main
    
    # Top Block
    # The block geometry (from boolean) sits at y=[0, h_block].
    # We move it up to the correct position.
    top_ref = c << final_block
    top_ref.movey(y_placement)
    
    # Bottom Block
    # We mirror the top geometry across the X-axis.
    # Since final_block is defined from y=0 upwards, mirroring it puts it y=0 downwards.
    # Then we move it to the correct negative offset.
    bot_ref = c << final_block
    bot_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
    bot_ref.movey(-y_placement)

    return c

# Generate and save the GDS
device = device_120_4()
device.write_gds("device.gds")