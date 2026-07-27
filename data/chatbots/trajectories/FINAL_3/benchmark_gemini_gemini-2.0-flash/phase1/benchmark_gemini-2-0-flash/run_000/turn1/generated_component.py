import gdsfactory as gf

@gf.cell
def mach_zehnder_interferometer():
    """
    Recreates a Mach-Zehnder Interferometer (MZI) using GDSFactory.
    """
    c = gf.Component("mzi")

    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=1.0, layer=(1, 0))
    
    # Define bends
    bend_radius = 10.0
    bend = gf.components.bend_euler(radius=bend_radius, cross_section=xs)
    
    # Define straight waveguide length
    straight_length = 50.0  # Adjust this value based on the footprint requirement. The straight length dominates the X-dimension.
    straight = gf.components.straight(length=straight_length, cross_section=xs)
    
    # Define coupler length and gap
    coupler_length = 10.0  # Adjust if needed to match visual.
    coupler_gap = 0.2 # Adjust if needed to match visual.
    coupler = gf.components.coupler_straight(length=coupler_length, gap=coupler_gap, cross_section=xs)


    # Create the input coupler
    input_coupler = c << coupler
    c.add_port("o1", port=input_coupler.ports["o1"])
    c.add_port("o2", port=input_coupler.ports["o2"])
    
    # Add the top arm components
    top_bend1 = c << bend
    top_bend1.connect("o1", input_coupler.ports["o3"])

    top_straight = c << straight
    top_straight.connect("o1", top_bend1.ports["o2"])

    top_bend2 = c << bend
    top_bend2.connect("o1", top_straight.ports["o2"])
    

    # Add the bottom arm components
    bottom_bend1 = c << bend
    bottom_bend1.connect("o1", input_coupler.ports["o4"])

    bottom_straight = c << straight
    bottom_straight.connect("o1", bottom_bend1.ports["o2"])

    bottom_bend2 = c << bend
    bottom_bend2.connect("o1", bottom_straight.ports["o2"])
    
    # Create the output coupler
    output_coupler = c << coupler
    output_coupler.connect("o3", top_bend2.ports["o2"])
    output_coupler.connect("o4", bottom_bend2.ports["o2"])
    c.add_port("o3", port=output_coupler.ports["o1"])
    c.add_port("o4", port=output_coupler.ports["o2"])

    return c

if __name__ == "__main__":
    mzi = mach_zehnder_interferometer()
    mzi.show()

    bbox = mzi.bbox()  # Call bbox as a method
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Component footprint: width={width:.2f} um, height={height:.2f} um")