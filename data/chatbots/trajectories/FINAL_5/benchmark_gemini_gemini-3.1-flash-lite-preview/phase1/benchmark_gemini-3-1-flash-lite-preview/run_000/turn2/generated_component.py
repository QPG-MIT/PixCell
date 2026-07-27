import gdsfactory as gf

# 1. Define a robust cross_section
# We set radius_min low enough to allow the tight U-bends
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=0.5)

@gf.cell
def periodic_straight(length=10.0, period=0.6, tooth_width=0.3, tooth_depth=0.2):
    """Creates a straight waveguide with periodic rectangular teeth."""
    c = gf.Component()
    
    # 1. Main waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # 2. Add periodic teeth
    # Calculate number of teeth
    n_teeth = int(length / period)
    start_x = -length / 2 + period / 2
    
    for i in range(n_teeth):
        x_pos = start_x + (i * period)
        
        # Add tooth above (top)
        t_top = c << gf.components.rectangle(size=(tooth_width, tooth_depth), layer=(1, 0))
        t_top.move((x_pos, 0.25 + tooth_depth/2))
        
        # Add tooth below (bottom)
        t_bot = c << gf.components.rectangle(size=(tooth_width, tooth_depth), layer=(1, 0))
        t_bot.move((x_pos, -0.25 - tooth_depth/2))
        
    # Expose ports
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def single_hook():
    """Creates one half of the device (a hook shape)."""
    c = gf.Component()
    
    # 1. Define primitives
    taper = c << gf.components.taper(length=2.0, width1=0.2, width2=0.5, cross_section=xs)
    wg = c << periodic_straight(length=8.0)
    bend = c << gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    
    # 2. Connect components
    wg.connect("o1", taper.ports["o2"])
    bend.connect("o1", wg.ports["o2"])
    
    # 3. Add Ports
    c.add_port("o1", port=taper.ports["o1"])
    c.add_port("o2", port=bend.ports["o2"])
    
    return c

@gf.cell
def device():
    c = gf.Component()
    
    # 1. Top hook
    top = c << single_hook()
    
    # 2. Bottom hook (mirrored)
    # We mirror across the horizontal axis and move down
    bot = c << single_hook()
    bot.mirror(p1=(0, 0), p2=(10, 0))
    bot.movey(-2.0)
    
    # 3. Center line
    center = c << gf.components.straight(length=12.0, cross_section=xs)
    center.movey(-1.0)
    
    return c

if __name__ == "__main__":
    # Create the device
    my_device = device()
    
    # Write to GDS
    my_device.write_gds("device.gds")
    
    # Show the layout
    my_device.show()