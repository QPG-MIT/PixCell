import gdsfactory as gf

@gf.cell
def improved_diverging_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create top waveguide: from (0,0) to (18, 1.5)
    top_path = gf.Path()
    top_path.append([(0, 0), (18, 1.5)])
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    
    # Create bottom waveguide: from (0,0) to (18, -1.5)
    bottom_path = gf.Path()
    bottom_path.append([(0, 0), (18, -1.5)])
    bottom_waveguide = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add both waveguides to the component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Add ports for connectivity
    c.add_port("o1_top", port=top_ref.ports["o1"])
    c.add_port("o2_top", port=top_ref.ports["o2"])
    c.add_port("o1_bottom", port=bottom_ref.ports["o1"])
    c.add_port("o2_bottom", port=bottom_ref.ports["o2"])
    
    return c

# Create and save the device
device = improved_diverging_waveguide_pair()
device.write_gds("improved_diverging_waveguide_pair.gds")