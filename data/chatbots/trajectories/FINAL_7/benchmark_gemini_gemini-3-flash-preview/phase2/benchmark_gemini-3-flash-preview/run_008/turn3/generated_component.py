import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device with a 5.5um x 3.0um footprint.
    Matches the stadium ring and the internal arm network with rectangular blocks.
    """
    layer = (1, 0)
    
    # 1. Dimensions based on footprint constraint
    total_w = 5.5
    total_h = 3.0
    ring_thick = 0.5
    
    # Stadium math: Total H = 2 * Radius_outer.
    # Radius_outer = 1.5.
    # Total W = 2 * Radius_outer + Straight_Length.
    # Straight_Length = 5.5 - 3.0 = 2.5
    r_outer = total_h / 2
    l_straight = total_w - (2 * r_outer)
    r_mean = r_outer - (ring_thick / 2)
    
    # 2. Create the Outer Stadium Ring
    # We build the path and center it at (0,0)
    ring_comp = gf.Component("ring_sub")
    p_ring = gf.path.straight(length=l_straight)
    p_ring += gf.path.arc(radius=r_mean, angle=180)
    p_ring += gf.path.straight(length=l_straight)
    p_ring += gf.path.arc(radius=r_mean, angle=180)
    
    r_ext = gf.path.extrude(p_ring, width=ring_thick, layer=layer)
    r_ref = ring_comp << r_ext
    # The path starts at (0,0) and ends back at (0,0), forming a loop.
    # Its bounding box spans from 0 to l_straight in x and 0 to 2*r_mean in y.
    r_ref.move((-l_straight / 2, -r_mean))
    
    # 3. Create the Internal Network
    internal_comp = gf.Component("internal_sub")
    
    # Wide vertical junction blocks at the left and right ends
    junc_w, junc_h = 0.75, 1.4
    x_junc_center = 1.95 # Positioned to overlap with inner ring curve for a seamless merge
    
    j_left = internal_comp << gf.components.rectangle(size=(junc_w, junc_h), centered=True, layer=layer)
    j_left.movex(-x_junc_center)
    j_right = internal_comp << gf.components.rectangle(size=(junc_w, junc_h), centered=True, layer=layer)
    j_right.movex(x_junc_center)
    
    # Arm Parameters
    arm_w = 0.25
    y_offset = 0.75
    # The diagonal parts connect the central blocks to the horizontal segments
    x_diagonal_end = 1.35 
    
    def add_arm(y_sign):
        y = y_sign * y_offset
        # Define the path of the arm: from left junction center to horizontal segment to right junction center
        pts = [(-x_junc_center, 0), (-x_diagonal_end, y), (x_diagonal_end, y), (x_junc_center, 0)]
        path = gf.Path(pts)
        internal_comp << gf.path.extrude(path, width=arm_w, layer=layer)
        
        # Add the two wide rectangular 'boxes' on the horizontal arm sections
        box_w, box_h = 0.9, 0.5
        box_gap = 0.15
        for dx in [-(box_w + box_gap)/2, (box_w + box_gap)/2]:
            b = internal_comp << gf.components.rectangle(size=(box_w, box_h), centered=True, layer=layer)
            b.move((dx, y))

    add_arm(1)   # Top arm
    add_arm(-1)  # Bottom arm
    
    # 4. Final Boolean Operation
    # Merging the ring and internal structure ensures no overlapping lines
    # and recreates the solid silhouette of the target image.
    device = gf.boolean(A=ring_comp, B=internal_comp, operation="or", layer=layer)
    
    return device

if __name__ == "__main__":
    c = recreated_device()
    c.show()
    c.write_gds("recreated_device.gds")