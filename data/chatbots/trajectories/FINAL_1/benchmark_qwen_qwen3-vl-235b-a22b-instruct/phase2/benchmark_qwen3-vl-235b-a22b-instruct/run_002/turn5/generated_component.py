import gdsfactory as gf

@gf.cell
def curved_waveguide_structure():
    c = gf.Component()
    
    # Define cross-section for input (1.7um wide as per footprint constraint)
    xs_input = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Define cross-section for tapered sections (0.85um wide)
    xs_tapered = gf.cross_section.cross_section(width=0.85, layer=(1, 0), radius=8.0)
    
    # Create input straight waveguide
    input_wg = c << gf.components.straight(length=10.0, cross_section=xs_input)
    input_wg.move((0, 0))
    
    # Create a short taper to reduce width
    taper_length = 2.0
    taper = c << gf.components.taper(length=taper_length, width1=1.7, width2=0.85)
    taper.connect("o1", input_wg.ports["o2"])
    
    # Create a Y-splitter using a more integrated approach
    # Create a path that goes straight then splits into two branches
    # Use a path with smooth transitions
    
    # Create top branch path
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=5.0))
    top_path.append(gf.path.euler(radius=8.0, angle=60, p=0.5))
    
    # Create bottom branch path
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=5.0))
    bottom_path.append(gf.path.euler(radius=8.0, angle=-60, p=0.5))
    
    # Create the two branches
    top_branch = c << gf.path.extrude(top_path, cross_section=xs_tapered)
    bottom_branch = c << gf.path.extrude(bottom_path, cross_section=xs_tapered)
    
    # Connect both branches to the taper output
    top_branch.connect("o1", taper.ports["o2"])
    bottom_branch.connect("o1", taper.ports["o2"])
    
    # Add ports
    c.add_port("in", port=input_wg.ports["o1"])
    c.add_port("top_out", port=top_branch.ports["o2"])
    c.add_port("bottom_out", port=bottom_branch.ports["o2"])
    
    return c

# Create and save the device
device = curved_waveguide_structure()
device.write_gds("curved_waveguide_structure.gds")