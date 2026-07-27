import gdsfactory as gf

@gf.cell
def recreate_curved_waveguides():
    """
    Recreates the converging curved waveguide geometry.
    Footprint constraint: 18um (length) x 3um (height).
    """
    # 1. Dimensions and Visual Tuning
    L = 18.0
    H = 3.0
    
    # We use a larger width to match the original image's thick profile.
    # We use a very small central gap to match the proximity in the image.
    width = 0.9 
    center_gap = 0.15 
    
    # 2. Define vertical coordinates for the centers
    # At the far ends, top edge should be at +1.5um, bottom edge at -1.5um.
    y_end_center = (H / 2) - (width / 2)  # 1.5 - 0.45 = 1.05
    
    # At the middle point, they should be separated by 'center_gap'.
    y_mid_center = (center_gap / 2) + (width / 2) # 0.075 + 0.45 = 0.525
    
    # The vertical displacement (dy) for the 9um S-bend segment
    dy = y_end_center - y_mid_center
    dx = L / 2
    
    c = gf.Component("final_coupler_recreation")
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 3. Build the Arm Template
    # We build a single 'valley' component first.
    # It starts at (0,0), dips down in the middle, and returns to y=0.
    arm = gf.Component("arm_template")
    s1 = arm << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    s2 = arm << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    s2.connect("o1", s1.ports["o2"])
    
    # 4. Assemble the Device
    # Place Top Arm (The Valley)
    top_ref = c << arm
    top_ref.movey(y_end_center)
    
    # Place Bottom Arm (The Hill)
    # Mirroring the valley component guarantees a perfect symmetrical hill shape.
    bot_ref = c << arm
    bot_ref.mirror_y()
    bot_ref.movey(-y_end_center)
    
    # Center the entire device horizontally
    c.movex(-L/2)
    
    # 5. Write to GDS (Ensures file production)
    c.write_gds("recreated_geometry.gds")
    
    return c

if __name__ == "__main__":
    # Execute the function to generate the file
    device = recreate_curved_waveguides()
    print("GDS file 'recreated_geometry.gds' has been successfully produced.")