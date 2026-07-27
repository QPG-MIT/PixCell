import gdsfactory as gf

# FIX: Explicitly set radius_min to a value smaller than our bend radius (2.0)
# to satisfy the Design Rule Check (DRC) constraints.
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=1.0 
)

@gf.cell
def grated_straight(length=8.0, period=0.5, tooth_width=0.25, tooth_height=0.3):
    """Creates a straight waveguide with grating teeth on both sides."""
    c = gf.Component()
    
    # Base waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add teeth
    tooth = gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
    num_teeth = int(length / period)
    
    # Place teeth on both sides
    for i in range(num_teeth):
        x_pos = (i * period) - (length / 2) + (period / 2)
        
        # Top teeth
        t_top = c << tooth
        t_top.move((x_pos, 0.25)) 
        
        # Bottom teeth
        t_bot = c << tooth
        t_bot.move((x_pos, -0.25 - tooth_height)) 
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape_assembly(bend_radius=2.0, arm_length=8.0):
    """Assembles a U-shape: Bend + 2 Grated Arms."""
    c = gf.Component()
    
    # Bend (180 degrees)
    bend = c << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    
    # Arms (grated)
    arm1 = c << grated_straight(length=arm_length)
    arm2 = c << grated_straight(length=arm_length)
    
    # Connect arms to the bend ports
    # bend_euler(angle=180) has ports o1 and o2 at the same end
    arm1.connect("o1", bend.ports["o1"])
    arm2.connect("o1", bend.ports["o2"])
    
    # Expose external ports at the open ends
    c.add_port("o1", port=arm1.ports["o2"])
    c.add_port("o2", port=arm2.ports["o2"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # 1. Top U-shape (Bend on the right)
    u_top = c << u_shape_assembly()
    u_top.movey(3.0) 
    
    # 2. Bottom U-shape (Bend on the left)
    u_bot = c << u_shape_assembly()
    u_bot.rotate(180) # Rotates 180 to put the bend on the left
    u_bot.movey(-3.0) 
    
    return c

if __name__ == "__main__":
    device = full_device()
    device.write_gds("device.gds")
    device.show()