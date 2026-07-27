import gdsfactory as gf

@gf.cell
def y_splitter():
    c = gf.Component()
    
    # Define cross-section (width based on footprint constraint)
    xs = gf.cross_section.cross_section(width=1.7, layer=(1, 0))
    
    # Create the Y-split using a single path with smooth transition
    # Start with input waveguide
    y_path = gf.Path()
    y_path.append(gf.path.straight(length=15.0))  # Input section
    
    # Add a small straight section before the split
    y_path.append(gf.path.straight(length=1.0))
    
    # Create the Y-split with smooth transitions
    # Use a small Euler bend for the top branch
    y_path.append(gf.path.euler(radius=3.0, angle=22.5, p=0.5))
    y_path.append(gf.path.straight(length=10.0))  # Top branch extension
    
    # Create the bottom branch (need to create a separate path for the bottom branch)
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=16.0))  # Input section + small extension
    bottom_path.append(gf.path.euler(radius=3.0, angle=-22.5, p=0.5))
    bottom_path.append(gf.path.straight(length=10.0))  # Bottom branch extension
    
    # Extrude the paths
    top_branch = gf.path.extrude(y_path, cross_section=xs)
    bottom_branch = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add to component
    c << top_branch
    c << bottom_branch
    
    # Add ports
    c.add_port("o1", port=top_branch.ports["o1"])  # Input port (same as bottom_branch.o1)
    c.add_port("o2", port=top_branch.ports["o2"])  # Top output port
    c.add_port("o3", port=bottom_branch.ports["o2"])  # Bottom output port
    
    # Flatten to avoid off-grid instance issues
    c.flatten()
    
    return c

# Create and save the device
device = y_splitter()
device.write_gds("y_splitter.gds")