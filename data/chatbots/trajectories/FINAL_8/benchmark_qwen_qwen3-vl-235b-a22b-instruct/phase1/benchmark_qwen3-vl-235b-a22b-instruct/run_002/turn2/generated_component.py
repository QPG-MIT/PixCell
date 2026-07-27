import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the central straight waveguides (4 parallel lines)
    straight_length = 120.0
    straight_gap = 0.5
    
    # Create central waveguides
    central_straights = []
    for i in range(4):
        straight = c << gf.components.straight(length=straight_length, cross_section=xs)
        straight.move((0, i * (0.5 + straight_gap)))
        central_straights.append(straight)
    
    # Create top curved structure using Euler bends
    # We'll create a path that forms the curved structure above
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=20))
    top_path.append(gf.path.euler(radius=20, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=40))
    top_path.append(gf.path.euler(radius=20, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=20))
    
    # Extrude the top path
    top_curve = c << gf.path.extrude(top_path, cross_section=xs)
    top_curve.move((0, 30.0))
    
    # Create bottom curved structure (mirrored)
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=20))
    bottom_path.append(gf.path.euler(radius=20, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=40))
    bottom_path.append(gf.path.euler(radius=20, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=20))
    
    # Extrude the bottom path
    bottom_curve = c << gf.path.extrude(bottom_path, cross_section=xs)
    bottom_curve.move((0, -30.0))
    bottom_curve.mirror()
    
    # Create input/output waveguides on the left side
    left_wgs = []
    for i in range(4):
        left_wg = c << gf.components.straight(length=10, cross_section=xs)
        left_wg.move((-10, i * (0.5 + straight_gap)))
        left_wgs.append(left_wg)
        
        # Connect to central waveguides
        left_wg.connect("o2", central_straights[i].ports["o1"])
    
    # Create input/output waveguides on the right side
    right_wgs = []
    for i in range(4):
        right_wg = c << gf.components.straight(length=10, cross_section=xs)
        right_wg.move((130, i * (0.5 + straight_gap)))
        right_wgs.append(right_wg)
        
        # Connect to central waveguides
        right_wg.connect("o1", central_straights[i].ports["o2"])
    
    # Add ports for external connections
    for i, wg in enumerate(left_wgs):
        c.add_port(f"left_{i+1}", port=wg.ports["o1"])
    
    for i, wg in enumerate(right_wgs):
        c.add_port(f"right_{i+1}", port=wg.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")