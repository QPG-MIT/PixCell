import gdsfactory as gf

# Define a custom cross-section with the small bend radius to prevent errors
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=0.5
)

@gf.cell
def straight_with_grating(length=6.0, period=0.5, tooth_width=0.25, tooth_height=0.3, wg_width=0.5):
    """Creates a straight waveguide with periodic grating teeth using a loop."""
    c = gf.Component()
    
    # 1. Add the central waveguide
    wg = c << gf.components.straight(length=length, width=wg_width, cross_section=xs)
    
    # 2. Add the grating teeth using a simple loop
    # We calculate the number of teeth based on the length
    num_teeth = int(length / period)
    tooth = gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
    
    for i in range(num_teeth):
        x_pos = i * period
        
        # Place top tooth
        t_top = c << tooth
        t_top.move((x_pos, wg_width / 2))
        
        # Place bottom tooth
        t_bot = c << tooth
        t_bot.move((x_pos, -wg_width / 2 - tooth_height))
    
    # Expose ports
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape_assembly(length=6.0):
    """Assembles the U-shape using port connections for a seamless join."""
    c = gf.Component()
    
    # Define primitives
    bend = gf.components.bend_euler(radius=1.0, angle=180, cross_section=xs)
    wg_arm = straight_with_grating(length=length)
    taper = gf.components.taper(length=2.0, width1=0.2, width2=0.5, cross_section=xs)
    
    # Assemble: Bend -> Arms -> Tapers
    turn = c << bend
    
    arm1 = c << wg_arm
    arm1.connect("o2", turn.ports["o1"])
    
    arm2 = c << wg_arm
    arm2.connect("o2", turn.ports["o2"])
    
    taper1 = c << taper
    taper1.connect("o2", arm1.ports["o1"])
    
    taper2 = c << taper
    taper2.connect("o2", arm2.ports["o1"])
    
    # Expose external ports
    c.add_port("o1", port=taper1.ports["o1"])
    c.add_port("o2", port=taper2.ports["o1"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # 1. Central waveguide
    center_wg = c << gf.components.straight(length=18.0, width=0.5, cross_section=xs)
    
    # 2. Top U-shape
    top_u = c << u_shape_assembly(length=8.0)
    top_u.movey(2.0)
    
    # 3. Bottom U-shape
    bot_u = c << u_shape_assembly(length=8.0)
    bot_u.mirror()
    bot_u.movey(-2.0)
    
    return c

if __name__ == "__main__":
    device = full_device()
    device.write_gds("device.gds")
    device.show()