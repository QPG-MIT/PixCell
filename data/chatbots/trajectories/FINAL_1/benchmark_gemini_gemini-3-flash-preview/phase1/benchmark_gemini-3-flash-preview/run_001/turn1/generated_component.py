import gdsfactory as gf

@gf.cell
def trident_spot_size_converter():
    """
    Recreates the trident-style spot-size converter (SSC) shown in the image.
    
    Constraint: 
    - Footprint: 40.0 um (length) x 1.7 um (width)
    
    The device consists of:
    1. A central inverse taper that narrows from left to right.
    2. Two side arms that taper outward and then curve away from the center.
    """
    c = gf.Component()

    # --- Dimensions based on 40.0 x 1.7 um footprint ---
    length_taper = 28.0
    length_bend = 12.0  # Total length = 28 + 12 = 40.0 um
    
    w_center_in = 0.6
    w_center_out = 0.05  # Tapers to a narrow tip
    
    w_side_in = 0.1
    w_side_out = 0.5
    
    gap_in = 0.08  # Initial gap between center and side waveguides
    
    # Final center-to-center pitch for the outer arms
    # To reach a total height of 1.7 um with 0.5 um wide waveguides:
    # Top edge = final_pitch/2 + w_side_out/2 = 0.6 + 0.25 = 0.85
    # Bottom edge = -0.6 - 0.25 = -0.85
    # Total width = 0.85 - (-0.85) = 1.7 um
    final_pitch = 1.2 

    # --- 1. Central Inverse Taper ---
    # We add a small straight section at the beginning to match the visual "stem"
    t_center = c << gf.components.taper(
        length=length_taper, 
        width1=w_center_in, 
        width2=w_center_out
    )

    # --- 2. Side Arm Tapers ---
    # Calculate starting y-position to maintain the desired gap
    y_start_side = w_center_in / 2 + gap_in + w_side_in / 2
    
    t_top = c << gf.components.taper(
        length=length_taper, 
        width1=w_side_in, 
        width2=w_side_out
    )
    t_top.movey(y_start_side)
    
    t_bot = c << gf.components.taper(
        length=length_taper, 
        width1=w_side_in, 
        width2=w_side_out
    )
    t_bot.movey(-y_start_side)

    # --- 3. Output S-Bends ---
    # Define cross section for the curved segments
    xs_side = gf.cross_section.cross_section(width=w_side_out)
    
    # Calculate vertical offset needed for the S-bend
    # Current center is at y_start_side, target is final_pitch / 2
    dy = (final_pitch / 2) - y_start_side
    
    # Add top bend
    b_top = c << gf.components.bend_s(
        size=(length_bend, dy), 
        cross_section=xs_side
    )
    b_top.connect("o1", t_top.ports["o2"])
    
    # Add bottom bend
    b_bot = c << gf.components.bend_s(
        size=(length_bend, -dy), 
        cross_section=xs_side
    )
    b_bot.connect("o1", t_bot.ports["o2"])

    # Expose ports for connectivity
    c.add_port("o1", port=t_center.ports["o1"])
    c.add_port("o2", port=b_top.ports["o2"])
    c.add_port("o3", port=b_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    component = trident_spot_size_converter()
    
    # Output footprint check
    bbox = component.bbox
    print(f"Device Footprint: {component.xsize:.2f} um x {component.ysize:.2f} um")
    
    # Show and save
    component.show()
    component.write_gds("trident_ssc.gds")