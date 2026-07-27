import gdsfactory as gf

@gf.cell
def y_splitter():
    c = gf.Component()
    
    # Define a single cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the branching path: 
    # Start with a straight section, then use an S-bend to split the path
    # into two separate arms.
    
    # 1. Path construction
    # We define the path from the center out. 
    # This creates a "Y" shape that we can then mirror.
    p = gf.Path()
    p.append(gf.path.straight(length=20))
    p.append(gf.path.euler(radius=10, angle=45, p=0.5)) # Curve outwards
    p.append(gf.path.straight(length=20))
    
    # 2. Extrude the path into geometry
    # Using extrude creates a single, unified component.
    splitter = c << gf.path.extrude(p, cross_section=xs)
    
    # 3. Mirror to create the other half
    # This completes the "H" or "Y" shape structure
    splitter_bottom = c << gf.path.extrude(p, cross_section=xs)
    splitter_bottom.mirror()
    
    # 4. Connect/Align them
    # Position them to form the unified central bar
    splitter.movey(5)
    splitter_bottom.movey(-5)
    
    # Add input/output ports for standard GDSFactory connectivity
    c.add_port("o1", port=splitter.ports["o1"])
    c.add_port("o2", port=splitter_bottom.ports["o1"])
    c.add_port("o3", port=splitter.ports["o2"])
    c.add_port("o4", port=splitter_bottom.ports["o2"])
    
    return c

# Create and save
device = y_splitter()
device.write_gds("y_splitter.gds")