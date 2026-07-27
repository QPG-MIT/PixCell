import gdsfactory as gf

# 1. Define a cross_section with a small radius_min to allow tight bends
xs = gf.cross_section.cross_section(
    width=0.5, 
    layer=(1, 0), 
    radius_min=0.5  # Allows for the tight bends seen in the image
)

@gf.cell
def corrugated_straight(length=10.0, period=0.5, tooth_width=0.2, tooth_height=0.2):
    """Creates a straight waveguide with periodic rectangular teeth."""
    c = gf.Component()
    
    # Add the base straight waveguide
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add periodic teeth (using references to avoid locked errors)
    num_teeth = int(length / period)
    for i in range(num_teeth):
        x_pos = (i * period) - (length / 2) + (period / 2)
        
        # Add tooth above
        t_top = c << gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
        t_top.move((x_pos, 0.35))
        
        # Add tooth below
        t_bot = c << gf.components.rectangle(size=(tooth_width, tooth_height), layer=(1, 0))
        t_bot.move((x_pos, -0.55))
        
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    return c

@gf.cell
def u_shape_device():
    """Creates one of the two U-shaped devices seen in the image."""
    c = gf.Component()
    
    # Components
    taper = gf.components.taper(length=2.0, width1=0.2, width2=0.5, cross_section=xs)
    wg_seg = corrugated_straight(length=10.0)
    bend = gf.components.bend_euler(radius=2.0, angle=180, cross_section=xs)
    
    # Assembly
    taper1 = c << taper
    wg1 = c << wg_seg
    bend1 = c << bend
    wg2 = c << wg_seg
    taper2 = c << taper
    
    # Connections
    wg1.connect("o1", taper1.ports["o2"])
    bend1.connect("o1", wg1.ports["o2"])
    wg2.connect("o1", bend1.ports["o2"])
    taper2.connect("o1", wg2.ports["o2"])
    
    # Expose main ports
    c.add_port("o1", port=taper1.ports["o1"])
    c.add_port("o2", port=taper2.ports["o2"])
    
    return c

@gf.cell
def full_assembly():
    c = gf.Component()
    
    # Add Top U-shape
    top = c << u_shape_device()
    
    # Add Bottom U-shape (mirror and move)
    bot = c << u_shape_device()
    bot.mirror(p1=(0, 0), p2=(10, 0))
    bot.movey(-5.0) # Separation between the two devices
    
    return c

if __name__ == "__main__":
    device = full_assembly()
    device.write_gds("final_device.gds")
    device.show()