import gdsfactory as gf

@gf.cell
def symmetric_coupler_device():
    """
    Recreates the symmetric coupler geometry using S-bend primitives.
    Fits precisely within an 18um x 3um footprint.
    """
    c = gf.Component("symmetric_coupler_18x3")

    # --- 1. Define Design Parameters ---
    total_length = 18.0
    total_height = 3.0
    wg_width = 0.6
    center_gap = 0.2
    
    # Calculate dimensions for the S-bend segments
    # Each waveguide is composed of two S-bends of half-length
    dx = total_length / 2  # 9.0 um
    
    # Vertical starting position (y-center of the waveguide at the ends)
    # To hit the 3um footprint edge: 1.5 - (width/2)
    y_outer_center = (total_height / 2) - (wg_width / 2)  # 1.2 um
    
    # Vertical center position (y-center of the waveguide at the pinch point)
    # Based on a 0.2um gap: (gap/2) + (width/2)
    y_inner_center = (center_gap / 2) + (wg_width / 2)    # 0.4 um
    
    # The vertical offset for one S-bend segment
    dy = y_inner_center - y_outer_center  # -0.8 um
    
    # Create the cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Construct Top Waveguide ---
    # Left S-bend (goes down)
    top_l = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    top_l.movey(y_outer_center)
    
    # Right S-bend (goes back up) - connects to the end of the left one
    top_r = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    top_r.connect("o1", top_l.ports["o2"])

    # --- 3. Construct Bottom Waveguide ---
    # Left S-bend (goes up)
    bot_l = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bot_l.movey(-y_outer_center)
    
    # Right S-bend (goes back down)
    bot_r = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    bot_r.connect("o1", bot_l.ports["o2"])

    # --- 4. Final Alignment ---
    # Center the entire component at (0,0) for the footprint requirement
    c.move(origin=c.center, destination=(0, 0))

    return c

if __name__ == "__main__":
    # Initialize the component
    device = symmetric_coupler_device()
    
    # Save to GDS file
    gds_filename = "symmetric_coupler.gds"
    device.write_gds(gds_filename)
    
    # Print status and verification
    print(f"GDS file successfully generated: {gds_filename}")
    print(f"Device Footprint: {device.dxsize:.1f} x {device.dysize:.1f} um")