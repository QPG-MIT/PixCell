import gdsfactory as gf

@gf.cell
def symmetric_coupler_final():
    """
    Recreates the symmetric coupler with smooth, large-radius curves 
    to fit the 18um x 3um footprint.
    
    We use two long S-bends per arm to maximize the bend radius 
    and match the visual 'flow' of the target image.
    """
    c = gf.Component("symmetric_coupler_final")
    
    # Footprint constraints
    total_length = 18.0
    total_height = 3.0
    half_length = total_length / 2
    
    # Waveguide properties
    # width=0.8 and outer_y=1.1 places the outer edges exactly at +/- 1.5um (3um total height)
    width = 0.8
    layer = (1, 0)
    
    # Define cross-section with a lowered radius_min to prevent geometry errors
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=2.0)
    
    # Vertical offsets
    # Outer vertical center: 1.1um (top edge at 1.5um)
    outer_y = 1.1
    # Inner vertical center: 0.45um (gap of 0.1um in the center)
    inner_y = 0.45
    dy = inner_y - outer_y # -0.65um displacement
    
    # --- Top Arm ---
    # We use two S-bends that meet in the middle (x = 9.0)
    t_left = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    t_left.movey(outer_y)
    
    t_right = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    t_right.connect("o1", t_left.ports["o2"])
    
    # --- Bottom Arm ---
    # Mirrored version of the top arm
    b_left = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    b_left.movey(-outer_y)
    
    b_right = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    b_right.connect("o1", b_left.ports["o2"])
    
    # Centering the component at (0,0)
    c.movex(-half_length)
    
    # Add external ports following catalog assembly pattern
    c.add_port("o1", port=t_left.ports["o1"])
    c.add_port("o2", port=b_left.ports["o1"])
    c.add_port("o3", port=t_right.ports["o2"])
    c.add_port("o4", port=b_right.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the device
    component = symmetric_coupler_final()
    
    # Verification of final footprint
    print(f"Component Dimensions: {component.dxsize:.2f} x {component.dysize:.2f} um")
    
    # Save and view
    component.write_gds("symmetric_coupler_fixed.gds")
    component.show()