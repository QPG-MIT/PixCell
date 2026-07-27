import gdsfactory as gf

# 1. Define custom cross-section to prevent radius errors
# We explicitly set radius_min to a small value so Euler bends work
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=0.1)

@gf.cell
def get_arm(length=10, radius=2):
    """
    Creates one arm of the device: A U-shape with teeth on the inner leg.
    """
    c = gf.Component()
    
    # Create the U-shape components
    bend = c << gf.components.bend_euler(radius=radius, angle=180, cross_section=xs)
    top_leg = c << gf.components.straight(length=length, cross_section=xs)
    bot_leg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Connect legs to the bend
    top_leg.connect("o1", bend.ports["o1"])
    bot_leg.connect("o1", bend.ports["o2"])
    
    # Add teeth to the inner leg (bot_leg)
    # Periodicity of teeth
    num_teeth = 20
    period = 0.6
    
    for i in range(num_teeth):
        # Create a rectangular tooth
        tooth = c << gf.components.rectangle(size=(0.2, 0.4), layer=(1, 0))
        
        # Calculate position: 
        # Along the length of the bottom leg
        # Aligning with the inner edge (y-offset relative to center of waveguide)
        x_pos = (i * period) + 1.0 
        y_pos = bot_leg.center[1] + 0.45 
        
        tooth.move((x_pos, y_pos))
        
    return c

@gf.cell
def final_device():
    c = gf.Component()
    
    # Define parameters
    arm_len = 15
    bend_rad = 2
    
    # Create two arms
    top_arm = c << get_arm(length=arm_len, radius=bend_rad)
    bot_arm = c << get_arm(length=arm_len, radius=bend_rad)
    
    # Position: Move top arm up, mirror and move bottom arm down
    top_arm.movey(2.0)
    
    bot_arm.mirror_y()
    bot_arm.movey(-2.0)
    
    # Add central divider
    # The divider sits between the two arms
    divider = c << gf.components.rectangle(size=(arm_len + bend_rad*2, 0.2), layer=(1, 0))
    divider.center = (top_arm.center[0] - bend_rad, 0)
    
    return c

# Generate the device
if __name__ == "__main__":
    device = final_device()
    device.write_gds("device_layout.gds")
    # device.show() # Uncomment to view in KLayout