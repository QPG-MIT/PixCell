import gdsfactory as gf

# Set radius to 5.0 to satisfy the constraint of CrossSection.radius_min 5.0
R = 5.0
xs = gf.cross_section.strip(width=0.5, layer=(1, 0))

@gf.cell
def grated_straight(length=10.0, period=0.5, tooth_width=0.25, tooth_height=0.3):
    """Creates a straight waveguide with gratings on both sides."""
    c = gf.Component()
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Grating teeth
    tooth = gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
    num_teeth = int(length / period)
    
    for i in range(num_teeth):
        x = (i * period) - (length / 2) + (period / 2)
        
        # Place Top Tooth
        t_top = c << tooth
        t_top.move((x, 0.25 + tooth_height/2))
        
        # Place Bottom Tooth
        t_bot = c << tooth
        t_bot.move((x, -0.25 - tooth_height/2))
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape():
    """Assembles a U-bend with two grated arms and two output hooks."""
    c = gf.Component()
    
    # 1. The main U-bend (180 degrees)
    # Using R=5.0 for the bend
    u_bend = c << gf.components.bend_euler(radius=R, angle=180, cross_section=xs)
    
    # 2. The grated straight sections
    arm_top = c << grated_straight(length=10.0)
    arm_bot = c << grated_straight(length=10.0)
    
    # Connect arms to the bend
    # bend_euler(angle=180) ports: o1 (bottom), o2 (top)
    arm_top.connect("o1", u_bend.ports["o2"])
    arm_bot.connect("o1", u_bend.ports["o1"])
    
    # 3. The Hooks (output bends)
    # Using 90-degree bends for the hooks
    hook_top = c << gf.components.bend_euler(radius=R, angle=90, cross_section=xs)
    hook_bot = c << gf.components.bend_euler(radius=R, angle=-90, cross_section=xs)
    
    hook_top.connect("o1", arm_top.ports["o2"])
    hook_bot.connect("o1", arm_bot.ports["o2"])
    
    # Expose external ports
    c.add_port("o1", port=hook_top.ports["o2"])
    c.add_port("o2", port=hook_bot.ports["o2"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # Top U-structure
    top = c << u_shape()
    top.movey(R + 1.0) # Separation based on radius
    
    # Bottom U-structure (Mirrored)
    bot = c << u_shape()
    bot.rotate(180)
    bot.movey(-(R + 1.0)) 
    
    return c

if __name__ == "__main__":
    device = full_device()
    device.write_gds("device.gds")
    device.show()