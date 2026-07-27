import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. PARAMETERS (derived from 5.5um x 3.0um footprint)
    # Total Outer Dimensions: 5.5 x 3.0
    R_OUTER = 1.5
    L_STRAIGHT_OUTER = 2.5 # 2.5 + (2 * 1.5) = 5.5
    
    # Inner hole dimensions (Visual estimate: ~0.5um top wall, ~0.9um side wall)
    H_INNER = 2.0
    W_INNER = 3.7
    R_INNER = H_INNER / 2 # 1.0
    L_STRAIGHT_INNER = W_INNER - 2 * R_INNER # 1.7
    
    # 2. HELPER TO MAKE STADIUM SHAPE
    # This avoids 'locked' errors by moving references, not components
    def make_stadium(l_straight, radius, layer):
        # Base shapes
        rect = gf.components.rectangle(size=(l_straight, 2 * radius), layer=layer, centered=True)
        circ = gf.components.circle(radius=radius, layer=layer)
        
        # Add caps to a container component to group them for Boolean
        caps = gf.Component()
        c1 = caps << circ
        c1.movex(-l_straight/2)
        c2 = caps << circ
        c2.movex(l_straight/2)
        
        # Boolean OR the center rectangle with the two end caps
        return gf.boolean(A=rect, B=caps, operation="or", layer=layer)

    # Generate the geometry
    outer_shape = make_stadium(L_STRAIGHT_OUTER, R_OUTER, layer)
    inner_shape = make_stadium(L_STRAIGHT_INNER, R_INNER, layer)
    
    # Create the hollow frame by subtracting inner from outer
    frame = gf.boolean(A=outer_shape, B=inner_shape, operation="not", layer=layer)
    c << frame
    
    # 3. INTERNAL ARMS
    arm_w = 0.16
    block_size = (0.8, 0.4)
    y_pos = 0.6  # Vertical distance from center for the arms
    block_x = 0.5 # Horizontal distance from center for blocks
    
    xs_arm = gf.cross_section.cross_section(width=arm_w, layer=layer)
    
    # Inner wall x-coordinate where arms connect
    inner_wall_x = W_INNER / 2 # 1.85
    
    for sign in [1, -1]:
        y = sign * y_pos
        
        # Add the two rectangular blocks per arm
        for x_sign in [1, -1]:
            # Always move the reference (returned by <<), never the library component
            rect_ref = c << gf.components.rectangle(size=block_size, layer=layer, centered=True)
            rect_ref.move((x_sign * block_x, y))
            
        # Create connecting path (center of side wall -> horizontal section -> center)
        pts = [
            (-inner_wall_x, 0),
            (-1.4, y),
            (1.4, y),
            (inner_wall_x, 0)
        ]
        path = gf.Path(pts)
        c << gf.path.extrude(path, cross_section=xs_arm)

    return c

if __name__ == "__main__":
    device = recreate_device()
    # Output footprint to console for verification
    print(f"Final Footprint: {device.xsize:.2f} x {device.ysize:.2f} um")
    device.show() # Opens in KLayout