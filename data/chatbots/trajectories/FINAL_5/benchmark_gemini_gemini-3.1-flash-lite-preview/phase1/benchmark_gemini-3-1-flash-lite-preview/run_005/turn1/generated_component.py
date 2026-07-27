import gdsfactory as gf

@gf.cell
def toothed_arm(bend_radius=1.5, straight_len=7.62):
    """Creates a U-shaped waveguide with periodic teeth on the inner edge."""
    c = gf.Component()
    
    # FIX: Define a custom cross_section with a small radius_min 
    # to avoid the ValueError regarding default tech limits.
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0), radius_min=0.1)
    
    # 1. Add U-turn
    # bend_euler is the standard for compact 180 turns
    bend = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    
    # 2. Add straight segments (two legs of the U)
    # Connecting ports o1 and o2 to create the U shape
    top_leg = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot_leg = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    top_leg.connect("o1", bend.ports["o1"])
    bot_leg.connect("o1", bend.ports["o2"])
    
    # 3. Add periodic teeth (rectangles)
    # The teeth are placed on the inner edge of the U-shape (bottom leg)
    num_teeth = 25
    tooth_width = 0.2
    tooth_height = 0.2
    period = 0.5
    
    # Align teeth along the straight section
    # Using the bottom leg as the host for the teeth
    for i in range(num_teeth):
        tooth = c << gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
        # Position: start at x=0 (the bend end)
        tooth.movex(i * period)
        # Position: y aligned with the waveguide edge
        tooth.movey(bot_leg.center[1] - 0.25)
        
    return c

@gf.cell
def device():
    c = gf.Component()
    
    # Parameters derived to meet the [18.24, 0.7] footprint
    # Width of bend (diameter) + 2x straight_len approx 18.24
    br = 1.5
    sl = 7.62
    
    # Create the two arms
    top_arm = c << toothed_arm(bend_radius=br, straight_len=sl)
    bot_arm = c << toothed_arm(bend_radius=br, straight_len=sl)
    
    # Position: mirror and offset the bottom arm
    bot_arm.mirror_y()
    bot_arm.movey(-1.0)
    top_arm.movey(1.0)
    
    # Add central divider line
    divider = c << gf.components.rectangle(size=(18.24, 0.05), layer=(1, 0))
    divider.center = (top_arm.center[0], 0)
    
    return c

if __name__ == "__main__":
    c = device()
    # Write to GDS
    c.write_gds("device_layout.gds")
    # c.show() # Uncomment to view