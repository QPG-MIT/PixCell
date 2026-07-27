import gdsfactory as gf

@gf.cell
def device_design():
    c = gf.Component()

    # 1. Define Dimensions derived from the 4.7um footprint
    # The total radius from center to tip is 2.35um (4.7 / 2).
    # We approximate the "petal" body and the "stem" tip dimensions from the image.
    r_petal_x = 0.9    # X-radius of the ellipse (Half length of the petal body)
    r_petal_y = 0.55   # Y-radius of the ellipse (Half width of the fat part)
    w_tip = 0.25       # Width of the straight tip
    
    # We overlap the tip slightly with the petal to ensure a solid connection 
    # without a gap or zero-width point.
    overlap = 0.1
    
    # Calculate tip length to satisfy the total radius constraint
    # Total R = (2 * r_petal_x) + l_tip - overlap
    # 2.35 = 1.8 + l_tip - 0.1  => l_tip = 0.65
    l_tip = 0.65

    # 2. Create Primitives
    # Define cross-section for the tip
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=(1, 0))
    
    # Create the petal using an Ellipse primitive
    # This creates a smooth, convex shape unlike the linear taper
    petal = gf.components.ellipse(radii=(r_petal_x, r_petal_y), layer=(1, 0))
    
    # Create the straight tip
    tip = gf.components.straight(length=l_tip, cross_section=xs_tip)

    # 3. Assemble one "Arm"
    arm = gf.Component("arm")
    
    # Add the petal. 
    # The ellipse is centered at (0,0) by default. 
    # We shift it by +r_petal_x so its left edge sits at x=0 (the center of the device).
    p_ref = arm << petal
    p_ref.move((r_petal_x, 0))
    
    # Add the tip.
    # We place it at the end of the petal, minus the overlap distance.
    # Petal ends at x = 2 * r_petal_x.
    t_ref = arm << tip
    t_ref.move((2 * r_petal_x - overlap, 0))
    
    # 4. Array the Arm
    # Rotate the arm assembly 4 times around the center (0,0)
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)

    return c

if __name__ == "__main__":
    component = device_design()
    component.write_gds("design.gds")
    component.show()