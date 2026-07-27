import gdsfactory as gf

@gf.cell
def curved_waveguide_structure():
    c = gf.Component()
    
    # Define cross-section for input (1.7um wide as per footprint constraint)
    xs_input = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Define cross-section for tapered sections (0.85um wide)
    # Set min_bend_radius to match our bend radius
    xs_tapered = gf.cross_section.cross_section(width=0.85, layer=(1, 0), radius=10.0)
    
    # Create input straight waveguide
    input_wg = c << gf.components.straight(length=10.0, cross_section=xs_input)
    input_wg.move((0, 0))
    
    # Create taper to split the waveguide
    taper_length = 5.0
    taper = c << gf.components.taper(length=taper_length, width1=1.7, width2=0.85)
    taper.connect("o1", input_wg.ports["o2"])
    
    # Create top branch with tapered cross-section
    top_straight = c << gf.components.straight(length=5.0, cross_section=xs_tapered)
    top_straight.connect("o1", taper.ports["o2"])
    top_straight.move((0, 0.85))  # Position above the center line
    
    # Create top Euler bend with tapered cross-section (radius increased to 10.0)
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=45, cross_section=xs_tapered)
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Create bottom branch with tapered cross-section
    bottom_straight = c << gf.components.straight(length=5.0, cross_section=xs_tapered)
    bottom_straight.connect("o1", taper.ports["o2"])
    bottom_straight.move((0, -0.85))  # Position below the center line
    
    # Create bottom Euler bend with tapered cross-section (radius increased to 10.0)
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-45, cross_section=xs_tapered)
    bottom_bend.connect("o1", bottom_straight.ports["o2"])
    
    # Add ports
    c.add_port("in", port=input_wg.ports["o1"])
    c.add_port("top_out", port=top_bend.ports["o2"])
    c.add_port("bottom_out", port=bottom_bend.ports["o2"])
    
    return c

# Create and save the device
device = curved_waveguide_structure()
device.write_gds("curved_waveguide_structure.gds")