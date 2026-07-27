import gdsfactory as gf

@gf.cell
def recreate_racetrack_device():
    """
    Recreates the device geometry from the provided image using 
    parametric primitives and boolean operations.
    """
    c = gf.Component("racetrack_device")
    layer = (1, 0)

    # 1. Dimensions based on [3.0, 5.5] footprint
    total_width = 5.5
    total_height = 3.0
    ring_thickness = 0.4
    straight_len = 2.5
    # The path radius is the center of the waveguide: (Height/2) - (thickness/2)
    path_radius = (total_height / 2) - (ring_thickness / 2) # 1.5 - 0.2 = 1.3

    # 2. Create the outer ring using Path and Extrusion
    # A racetrack is: straight -> 180 deg arc -> straight -> 180 deg arc
    p = gf.path.straight(length=straight_len)
    p += gf.path.arc(radius=path_radius, angle=180)
    p += gf.path.straight(length=straight_len)
    p += gf.path.arc(radius=path_radius, angle=180)
    
    xs = gf.cross_section.cross_section(width=ring_thickness, layer=layer)
    ring = gf.path.extrude(p, cross_section=xs)
    
    # Add ring and center it
    ring_ref = c << ring
    ring_ref.movex(-straight_len / 2)

    # 3. Create Internal Structures (Side Blocks and Rails)
    # Side blocks provide the 'base' on the curved ends for the internal rails
    block_w = 0.7
    block_h = 1.4
    block_offset = 1.6 # Position to overlap with the inner curve start
    
    b_left = gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
    b_right = gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
    
    # Place blocks
    bl_ref = c << b_left
    bl_ref.movex(-block_offset)
    br_ref = c << b_right
    br_ref.movex(block_offset)

    # 4. Create the horizontal rails with pads
    pad_w = 0.95
    pad_h = 0.5
    rail_y = 0.55 # Offset from center for top and bottom rails
    conn_width = 0.2 # Thickness of the connecting 'rails'
    center_gap = 0.1 # Small gap/segment in the very center

    def add_rail_elements(y_pos):
        # Central connector
        mid = c << gf.components.rectangle(size=(center_gap, conn_width), layer=layer, centered=True)
        mid.movey(y_pos)
        
        # Left and Right Pads
        p_left = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p_left.move((-(pad_w/2 + center_gap/2), y_pos))
        
        p_right = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p_right.move((pad_w/2 + center_gap/2, y_pos))
        
        # Connectors to side blocks
        # Calculate distance between pad edge and block edge
        inner_block_edge = block_offset - (block_w / 2)
        outer_pad_edge = pad_w + (center_gap / 2)
        conn_l = inner_block_edge - outer_pad_edge
        
        cl = c << gf.components.rectangle(size=(conn_l, conn_width), layer=layer, centered=True)
        cl.movex(-(outer_pad_edge + conn_l/2))
        cl.movey(y_pos)
        
        cr = c << gf.components.rectangle(size=(conn_l, conn_width), layer=layer, centered=True)
        cr.movex(outer_pad_edge + conn_l/2)
        cr.movey(y_pos)

    add_rail_elements(rail_y)  # Top rail
    add_rail_elements(-rail_y) # Bottom rail

    # 5. Boolean Unification
    # To match the single solid black shape in the PNG, we perform a boolean OR
    # of all elements currently in the component.
    final_component = gf.Component("final_device")
    unified_shape = gf.boolean(A=c, B=c, operation="or", layer=layer)
    final_component << unified_shape

    return final_component

if __name__ == "__main__":
    device = recreate_racetrack_device()
    device.show() # Opens in KLayout
    device.write_gds("recreated_device.gds")