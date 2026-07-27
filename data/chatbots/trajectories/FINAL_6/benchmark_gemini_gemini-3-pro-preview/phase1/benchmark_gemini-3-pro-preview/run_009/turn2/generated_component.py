import gdsfactory as gf

@gf.cell
def star_cross_device():
    """
    Generates a 4-lobed cross device.
    Refined parameters to match the blunter petals and robust tips of the reference image.
    
    Footprint: 4.7 um x 4.7 um
    """
    c = gf.Component()
    
    # 1. Dimensional Parameters
    footprint = 4.7
    half_size = footprint / 2.0  # 2.35 um limit
    
    # Ellipse Dimensions (The Lobes)
    # Reduced major_radius (from 1.9 to 1.75) makes the ellipse 'terminate' earlier 
    # relative to its sharp tip, creating a blunter transition into the stub.
    # Increased minor_radius (from 0.75 to 0.82) adds volume to the center.
    lobe_major_radius = 1.75
    lobe_minor_radius = 0.82
    
    # Stub Dimensions (The Tips)
    # Increased width (from 0.35 to 0.52) to match the visual weight of the ports.
    stub_width = 0.52
    
    # Length is set to ensure it reaches the 2.35um boundary and overlaps 
    # the ellipse sufficiently. 
    # Overlap region: Ellipse ends at 1.75, Boundary at 2.35. Gap is 0.6.
    # A length of 0.85 ensures a ~0.25um overlap for a seamless union.
    stub_length = 0.85
    
    # 2. Define Primitives
    # Main elliptical body
    ellipse = gf.components.ellipse(
        radii=(lobe_major_radius, lobe_minor_radius), 
        layer=(1, 0)
    )
    
    # Rectangular port tip
    stub = gf.components.rectangle(
        size=(stub_length, stub_width), 
        layer=(1, 0), 
        centered=True
    )

    # 3. Assembly
    # Add Center Cross (Horizontal and Vertical Ellipses)
    c << ellipse
    v_lobe = c << ellipse
    v_lobe.rotate(90)
    
    # Add Port Stubs
    # Calculate position: Center the stub so its outer edge aligns with half_size
    stub_center_pos = half_size - (stub_length / 2.0)
    
    # Right
    s_right = c << stub
    s_right.movex(stub_center_pos)
    
    # Left
    s_left = c << stub
    s_left.movex(-stub_center_pos)
    
    # Top
    s_top = c << stub
    s_top.rotate(90)
    s_top.movey(stub_center_pos)
    
    # Bottom
    s_bot = c << stub
    s_bot.rotate(90)
    s_bot.movey(-stub_center_pos)
    
    return c

if __name__ == "__main__":
    # Create and display
    device = star_cross_device()
    device.show()
    
    # Verify dimensions
    print(f"Device width: {device.size_info.width:.2f} um")
    print(f"Device height: {device.size_info.height:.2f} um")
    
    # Save
    device.write_gds("star_cross_refined.gds")