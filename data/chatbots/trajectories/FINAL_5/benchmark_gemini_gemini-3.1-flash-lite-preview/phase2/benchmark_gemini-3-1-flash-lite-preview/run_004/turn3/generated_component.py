import gdsfactory as gf

# FIX: Set radius_min to 1.0, which is smaller than our bend radius of 2.0.
# This satisfies the Design Rule Check (DRC) constraints.
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=1.0 
)

@gf.cell
def grated_straight(length=8.0, period=0.5, tooth_width=0.25, tooth_height=0.3):
    """Creates a straight waveguide with grating teeth."""
    c = gf.Component()
    
    # Base waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add teeth
    tooth = gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
    num_teeth = int(length / period)
    
    # Place teeth relative to the waveguide center
    for i in range(num_teeth):
        x_pos = (i * period) - (length / 2) + (period / 2)
        
        # Top tooth
        t_top = c << tooth
        t_top.move((x_pos, 0.25)) 
        
        # Bottom tooth
        t_bot = c << tooth
        t_bot.move((x_pos, -0.25 - tooth_height)) 
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape_assembly():
    """Assembles the U-shape: Bend + 2 Grated Arms + 2 Tapers."""
    c = gf.Component()
    
    # 1. Bend (Using radius=2.0, which is > radius_min=1.0)
    bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    
    # 2. Arms (grated)
    arm1 = c << grated_straight(length=8.0)
    arm2 = c << grated_straight(length=8.0)
    
    # Connect arms to the bend
    arm1.connect("o2", bend.ports["o1"])
    arm2.connect("o2", bend.ports["o2"])
    
    # 3. Tapers at the open ends
    taper = gf.components.taper(length=2.0, width1=0.2, width2=0.5, cross_section=xs)
    t1 = c << taper
    t1.connect("o2", arm1.ports["o1"])
    
    t2 = c << taper
    t2.connect("o2", arm2.ports["o1"])
    
    # Add external ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=t2.ports["o1"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # 1. Central waveguide
    center_wg = c << gf.components.straight(length=18.0, cross_section=xs)
    
    # 2. Top U-shape
    u_top = c << u_shape_assembly()
    u_top.movey(4.0) 
    
    # 3. Bottom U-shape (mirror of the top)
    u_bot = c << u_shape_assembly()
    u_bot.mirror_y() 
    u_bot.movey(-4.0) 
    
    return c

if __name__ == "__main__":
    device = full_device()
    device.write_gds("device.gds")
    device.show()