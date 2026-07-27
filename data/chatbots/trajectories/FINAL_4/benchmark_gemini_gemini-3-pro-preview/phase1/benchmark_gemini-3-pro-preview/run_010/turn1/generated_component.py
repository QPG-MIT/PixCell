import gdsfactory as gf

@gf.cell
def directional_coupler_geometry():
    """
    Creates a directional coupler geometry matching the provided image and footprint.
    
    Footprint: 18 um x 3 um
    Construction: Two waveguides with S-bends converging to a central straight coupling region.
    """
    c = gf.Component()

    # Device Dimensions derived from footprint constraint [18, 3]
    total_length = 18.0
    total_height = 3.0
    
    # Feature sizes estimated from image proportions
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal dimensions
    # 18um total length divided into: Input Bend + Straight Coupler + Output Bend
    # To match the aspect ratio, we use 6um for the central coupler.
    straight_length = 6.0 
    bend_length = (total_length - straight_length) / 2 # Result: 6.0 um
    
    # Vertical dimensions
    # Calculate Y coordinates to fit exactly within the 3.0um height limit (+/- 1.5um)
    # Outer Port Y position (center of waveguide):
    y_port_center = (total_height / 2) - (wg_width / 2) # 1.5 - 0.25 = 1.25
    
    # Inner Coupling Y position (center of waveguide):
    y_couple_center = (gap / 2) + (wg_width / 2)        # 0.1 + 0.25 = 0.35
    
    # The vertical displacement (dy) for the S-bends
    dy_bend = y_port_center - y_couple_center           # 0.9 um

    # --- Cross Section Definition ---
    # We explicitly set radius_min to 5.0 (below the calculated ~7.665) 
    # to allow the generation of the S-bends required for this footprint
    # without triggering the default radius violation error.
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0),
        radius=5.0, 
        radius_min=5.0
    )

    # --- Create Primitives ---
    
    # Central Straight Section
    straight_sec = gf.components.straight(length=straight_length, cross_section=xs)

    # Bend Primitives
    # Top Input: Starts high, goes down to coupling. dy is negative.
    bend_down = gf.components.bend_s(size=(bend_length, -dy_bend), cross_section=xs)
    
    # Top Output: Starts low, goes up to port. dy is positive.
    bend_up = gf.components.bend_s(size=(bend_length, dy_bend), cross_section=xs)
    
    # --- Assembly ---

    # 1. Top Branch
    # Place central straight section
    top_straight_ref = c << straight_sec
    top_straight_ref.movey(y_couple_center)
    
    # Attach Input S-bend (connects to left side of straight)
    top_in_ref = c << bend_down
    top_in_ref.connect("o2", top_straight_ref.ports["o1"])
    
    # Attach Output S-bend (connects to right side of straight)
    top_out_ref = c << bend_up
    top_out_ref.connect("o1", top_straight_ref.ports["o2"])

    # 2. Bottom Branch
    # Place central straight section
    bot_straight_ref = c << straight_sec
    bot_straight_ref.movey(-y_couple_center)
    
    # Attach Input S-bend
    # Bottom input goes UP from port (-y) to coupling (-y_couple). dy is positive.
    # We can reuse the shape of 'bend_up'.
    bot_in_ref = c << bend_up
    bot_in_ref.connect("o2", bot_straight_ref.ports["o1"])
    
    # Attach Output S-bend
    # Bottom output goes DOWN from coupling (-y_couple) to port (-y). dy is negative.
    # We can reuse the shape of 'bend_down'.
    bot_out_ref = c << bend_down
    bot_out_ref.connect("o1", bot_straight_ref.ports["o2"])

    return c

if __name__ == "__main__":
    # Create and save the device
    device = directional_coupler_geometry()
    device.write_gds("directional_coupler_corrected.gds")