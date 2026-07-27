import gdsfactory as gf

@gf.cell
def recreate_cross_device():
    """
    Recreates the clover-cross geometry.
    Footprint: 4.7 um x 4.7 um.
    
    This version avoids 'locked cell' errors by using references for transformations.
    """
    layer = (1, 0)
    
    # 1. Define base dimensions
    total_length = 4.7
    waist_width = 0.35
    r_major = 1.05  # Petal length
    r_minor = 0.55  # Petal bulge width
    offset = 1.15   # Petal center offset from origin
    
    # 2. Create the primitives (the 'blueprints')
    spine_cell = gf.components.cross(length=total_length, width=waist_width, layer=layer)
    ellipse_h_cell = gf.components.ellipse(radii=(r_major, r_minor), layer=layer)
    ellipse_v_cell = gf.components.ellipse(radii=(r_minor, r_major), layer=layer)
    
    # 3. Create container components for the translated petals
    # This avoids modifying the original locked primitive cells.
    p_right = gf.Component("p_right")
    p_right.add_ref(ellipse_h_cell).movex(offset)
    
    p_left = gf.Component("p_left")
    p_left.add_ref(ellipse_h_cell).movex(-offset)
    
    p_top = gf.Component("p_top")
    p_top.add_ref(ellipse_v_cell).movey(offset)
    
    p_bottom = gf.Component("p_bottom")
    p_bottom.add_ref(ellipse_v_cell).movey(-offset)
    
    # 4. Use Boolean OR to merge the spine and petals into a single polygon
    # gf.boolean returns a new Component with the resulting geometry.
    result = gf.boolean(
        A=spine_cell,
        B=[p_right, p_left, p_top, p_bottom],
        operation="or",
        layer=layer
    )
    result.name = "recreated_cross"
    
    return result

if __name__ == "__main__":
    # Create the component
    c = recreate_cross_device()
    
    # Save the GDS file
    filename = "recreated_device.gds"
    c.write_gds(filename)
    
    print(f"Success! GDS file produced: {filename}")
    
    # If you have KLayout or another viewer configured, you can call:
    # c.show()