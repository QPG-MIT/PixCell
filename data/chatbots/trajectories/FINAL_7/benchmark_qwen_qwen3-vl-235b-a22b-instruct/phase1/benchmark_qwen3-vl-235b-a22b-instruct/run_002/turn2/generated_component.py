import gdsfactory as gf

@gf.cell
def racetrack_resonator_with_couplers():
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the racetrack resonator
    straight_length = 2.0
    bend_radius = 0.75
    
    # Create the path for the racetrack
    path = gf.path.straight(length=straight_length)
    path += gf.path.euler(radius=bend_radius, angle=180)
    path += gf.path.straight(length=straight_length)
    path += gf.path.euler(radius=bend_radius, angle=180)
    
    # Extrude the path to create the racetrack
    racetrack = gf.path.extrude(path, cross_section=xs)
    
    # Create the coupling gaps (rectangles to subtract)
    gap_width = 0.2
    gap_length = 0.5
    
    # Create gap components
    top_gap1 = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    top_gap2 = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    bottom_gap1 = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    bottom_gap2 = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    
    # Create a new component for the boolean operation
    racetrack_component = gf.Component()
    racetrack_ref = racetrack_component << racetrack
    
    # Create components for gaps with proper positioning
    # Position gaps in the center of the straight sections
    # For the top straight section
    top_gap1_component = gf.Component()
    top_gap1_ref = top_gap1_component << top_gap1
    top_gap1_ref.move((straight_length/2 - gap_length/2 - 0.3, bend_radius + 0.1))
    
    top_gap2_component = gf.Component()
    top_gap2_ref = top_gap2_component << top_gap2
    top_gap2_ref.move((straight_length/2 - gap_length/2 + 0.3, bend_radius + 0.1))
    
    # For the bottom straight section
    bottom_gap1_component = gf.Component()
    bottom_gap1_ref = bottom_gap1_component << bottom_gap1
    bottom_gap1_ref.move((straight_length/2 - gap_length/2 - 0.3, -bend_radius - 0.1))
    
    bottom_gap2_component = gf.Component()
    bottom_gap2_ref = bottom_gap2_component << bottom_gap2
    bottom_gap2_ref.move((straight_length/2 - gap_length/2 + 0.3, -bend_radius - 0.1))
    
    # Perform boolean operations
    # Subtract all gaps from racetrack
    result = gf.boolean(racetrack_component, top_gap1_component, operation="not", layer=(1, 0))
    result = gf.boolean(result, top_gap2_component, operation="not", layer=(1, 0))
    result = gf.boolean(result, bottom_gap1_component, operation="not", layer=(1, 0))
    result = gf.boolean(result, bottom_gap2_component, operation="not", layer=(1, 0))
    
    # Add the final result to our main component
    final_ref = c << result
    
    # Add ports from original racetrack
    c.add_port("o1", port=racetrack.ports["o1"])
    c.add_port("o2", port=racetrack.ports["o2"])
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")