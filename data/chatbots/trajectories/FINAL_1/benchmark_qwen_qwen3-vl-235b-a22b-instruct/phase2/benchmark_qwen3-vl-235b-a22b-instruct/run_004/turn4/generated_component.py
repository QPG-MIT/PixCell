import gdsfactory as gf

@gf.cell
def y_splitter():
    c = gf.Component()
    
    # Define cross-section (width based on footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create the input waveguide
    input_wg = c << gf.components.straight(length=15.0, cross_section=xs)
    input_wg.move((0, 0))
    
    # Create the Y-split using a path with specific points
    # Create the top branch path
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=15.0))  # Input section
    top_path.append(gf.path.straight(length=1.0))    # Small extension at split point
    # Add a small Euler bend to create the angle for the top branch
    top_path.append(gf.path.euler(radius=2.0, angle=45, p=0.1))
    top_path.append(gf.path.straight(length=10.0))   # Top branch extension
    
    # Create the bottom branch path
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=15.0))  # Input section
    bottom_path.append(gf.path.straight(length=1.0))    # Small extension at split point
    # Add a small Euler bend to create the angle for the bottom branch
    bottom_path.append(gf.path.euler(radius=2.0, angle=-45, p=0.1))
    bottom_path.append(gf.path.straight(length=10.0))   # Bottom branch extension
    
    # Extrude the paths
    top_branch = gf.path.extrude(top_path, cross_section=xs)
    bottom_branch = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add to component
    c << top_branch
    c << bottom_branch
    
    # Add ports
    c.add_port("o1", port=top_branch.ports["o1"])  # Input port
    c.add_port("o2", port=top_branch.ports["o2"])  # Top output port
    c.add_port("o3", port=bottom_branch.ports["o2"])  # Bottom output port
    
    # Flatten to avoid off-grid instance issues
    c.flatten()
    
    return c

# Create and save the device
device = y_splitter()
device.write_gds("y_splitter.gds")