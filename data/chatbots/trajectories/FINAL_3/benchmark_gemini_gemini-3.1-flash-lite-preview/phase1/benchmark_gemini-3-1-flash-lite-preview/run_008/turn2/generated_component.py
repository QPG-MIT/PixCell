import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    """
    Constructs the coupler using standard assembly. 
    This avoids manual port creation and complex path logic.
    """
    c = gf.Component("flared_coupler")
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 1. Create the center coupling section (the "eye" part)
    # This is a standard primitive in the catalog
    coupler = c << gf.components.coupler_straight(length=40, gap=1.0, cross_section=xs)
    
    # 2. Add S-bends to the input ports (o1, o3) and output ports (o2, o4)
    # We use bend_s to flare out the waveguide
    bend_in1 = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    bend_in2 = c << gf.components.bend_s(size=(20, -2), cross_section=xs)
    
    bend_out1 = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    bend_out2 = c << gf.components.bend_s(size=(20, -2), cross_section=xs)
    
    # 3. Connect everything
    # We connect the S-bends to the coupler ports
    # Input side
    bend_in1.connect("o2", coupler.ports["o1"])
    bend_in2.connect("o2", coupler.ports["o3"])
    
    # Output side
    bend_out1.connect("o1", coupler.ports["o2"])
    bend_out2.connect("o1", coupler.ports["o4"])
    
    # We don't need to manually add_port here; 
    # the component automatically contains the ports of the connected sub-elements.
    
    return c

if __name__ == "__main__":
    device = flared_coupler_device()
    # Save the GDS file
    device.write_gds("flared_coupler.gds")
    # Open in KLayout
    device.show()