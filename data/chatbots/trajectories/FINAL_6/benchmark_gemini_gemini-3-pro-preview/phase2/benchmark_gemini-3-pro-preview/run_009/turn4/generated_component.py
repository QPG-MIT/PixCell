import gdsfactory as gf

@gf.cell
def star_cross_device():
    """
    Generates a 4-lobed cross device with smooth transitions to waveguide ports.
    
    Refined parameters (Iteration 4) to eliminate the "muffin top" artifact
    and match the slender, tapered look of the target image.
    
    Geometry:
    - 4 Elliptical lobes forming the body (slender aspect ratio).
    - 4 Rectangular stubs forming the waveguide ports.
    - Transition point pushed outward to minimize width discontinuity.
    
    Footprint: 4.7 um x 4.7 um
    """
    c = gf.Component()
    
    # 1. Dimensional Parameters
    footprint = 4.7
    radius_bound = footprint / 2.0  # Device boundary at +/- 2.35 um
    
    # Lobe Dimensions
    # Major radius increased (2.0 -> 2.15) and Minor radius decreased (0.6 -> 0.55).
    # This creates a longer, thinner taper that matches the target's "star" shape better.
    lobe_major_radius = 2.15
    lobe_minor_radius = 0.55
    
    # Stub Dimensions
    # Width reduced slightly to 0.32 to match the thin lines in the target.
    stub_width = 0.32
    
    # Stub Length calculation
    # We shorten the stub to 0.4 um so it attaches further out along the ellipse.
    # Attachment x-coord: 2.35 - 0.4 = 1.95 um.
    # At x=1.95, the ellipse width is approx 0.46 um, which is close to the 
    # stub width (0.32 um), creating a smooth "shoulder" transition.
    stub_length = 0.4
    
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
    
    # Add Horizontal Lobe
    c << ellipse
    
    # Add Vertical Lobe (Rotated 90 degrees)
    v_lobe_ref = c << ellipse
    v_lobe_ref.rotate(90)
    
    # Add Port Stubs
    # Calculate center position to align outer edge with radius_bound
    stub_center_dist = radius_bound - (stub_length / 2.0)
    
    # Right Stub (East)
    s_right = c << stub
    s_right.movex(stub_center_dist)
    
    # Left Stub (West)
    s_left = c << stub
    s_left.movex(-stub_center_dist)
    
    # Top Stub (North)
    s_top = c << stub
    s_top.rotate(90)
    s_top.movey(stub_center_dist)
    
    # Bottom Stub (South)
    s_bot = c << stub
    s_bot.rotate(90)
    s_bot.movey(-stub_center_dist)
    
    # 4. Add Ports (Standard GDSFactory practice)
    c.add_port("o1", center=(radius_bound, 0), width=stub_width, orientation=0, layer=(1,0))
    c.add_port("o2", center=(0, radius_bound), width=stub_width, orientation=90, layer=(1,0))
    c.add_port("o3", center=(-radius_bound, 0), width=stub_width, orientation=180, layer=(1,0))
    c.add_port("o4", center=(0, -radius_bound), width=stub_width, orientation=270, layer=(1,0))

    return c

if __name__ == "__main__":
    # Create the device
    device = star_cross_device()
    
    # Verify dimensions
    print(f"Device width: {device.size_info.width:.2f} um")
    print(f"Device height: {device.size_info.height:.2f} um")
    
    # Show and Save
    device.show()
    device.write_gds("star_cross_refined_v4.gds")