import gdsfactory as gf

# Define a custom cross-section with a smaller minimum radius
# This overrides the default PDK constraint of 5.0
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=0.5
)

@gf.cell
def straight_with_grating(length=5.0, period=0.4, grating_width=0.2, wg_width=0.5):
    """Creates a straight waveguide with periodic grating stripes."""
    c = gf.Component()
    
    # Add the central straight waveguide
    wg = c << gf.components.straight(length=length, width=wg_width, cross_section=xs)
    
    # Add periodic grating rectangles
    num_periods = int(length / period)
    for i in range(num_periods):
        x_pos = i * period
        
        # Add top grating
        top_rect = c << gf.components.rectangle(size=(period / 2, grating_width), layer=(1, 0))
        top_rect.move((x_pos, wg_width / 2))
        
        # Add bottom grating
        bot_rect = c << gf.components.rectangle(size=(period / 2, grating_width), layer=(1, 0))
        bot_rect.move((x_pos, -wg_width / 2 - grating_width))
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape(length=5.0):
    """Creates a U-shaped structure with grating and tapers."""
    c = gf.Component()
    
    # Primitives
    # Using the custom cross_section 'xs' for the bend
    bend = gf.components.bend_euler(radius=1.0, angle=180, cross_section=xs)
    arm = straight_with_grating(length=length)
    
    # Assemble
    turn = c << bend
    
    # Attach arms
    arm1 = c << arm
    arm1.connect("o2", turn.ports["o1"])
    
    arm2 = c << arm
    arm2.connect("o2", turn.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=arm1.ports["o1"])
    c.add_port("o2", port=arm2.ports["o1"])
    
    return c

@gf.cell
def full_device():
    c = gf.Component()
    
    # Central straight waveguide
    center_wg = c << gf.components.straight(length=18.0, width=0.5, cross_section=xs)
    
    # Top U-shape
    top_u = c << u_shape(length=8.0)
    # Align to center waveguide (adjusting Y offset based on visual)
    top_u.move((0, 1.0))
    
    # Bottom U-shape
    bot_u = c << u_shape(length=8.0)
    bot_u.mirror()
    bot_u.move((0, -1.0))
    
    return c

if __name__ == "__main__":
    device = full_device()
    device.write_gds("device.gds")
    device.show()