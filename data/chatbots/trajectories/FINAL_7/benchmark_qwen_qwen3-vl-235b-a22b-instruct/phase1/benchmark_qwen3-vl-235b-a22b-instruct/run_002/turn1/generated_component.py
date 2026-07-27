import gdsfactory as gf

@gf.cell
def racetrack_resonator_with_couplers():
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the racetrack resonator
    straight_length = 2.5
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
    top_gap = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    bottom_gap = gf.components.rectangle(size=(gap_length, gap_width), layer=(1, 0))
    
    # Create a component to hold the final structure
    final = gf.Component()
    
    # Add racetrack to final component
    racetrack_ref = final << racetrack
    
    # Add gaps to final component
    top_gap_ref = final << top_gap
    top_gap_ref.move((straight_length/2 - gap_length/2, bend_radius + 0.1))
    
    bottom_gap_ref = final << bottom_gap
    bottom_gap_ref.move((straight_length/2 - gap_length/2, -bend_radius - 0.1))
    
    # Create the final structure using boolean operations
    # We need to create separate components for the boolean operation
    racetrack_component = gf.Component()
    racetrack_component_ref = racetrack_component << racetrack
    
    # Create component with top gap
    top_gap_component = gf.Component()
    top_gap_component_ref = top_gap_component << top_gap
    top_gap_component_ref.move((straight_length/2 - gap_length/2, bend_radius + 0.1))
    
    # Create component with bottom gap
    bottom_gap_component = gf.Component()
    bottom_gap_component_ref = bottom_gap_component << bottom_gap
    bottom_gap_component_ref.move((straight_length/2 - gap_length/2, -bend_radius - 0.1))
    
    # Perform boolean operations
    # First subtract top gap
    result = gf.boolean(racetrack_component, top_gap_component, operation="not", layer=(1, 0))
    
    # Then subtract bottom gap
    result = gf.boolean(result, bottom_gap_component, operation="not", layer=(1, 0))
    
    # Add the result to our main component
    final_result = c << result
    
    # Add ports from the original racetrack
    c.add_port("o1", port=racetrack.ports["o1"])
    c.add_port("o2", port=racetrack.ports["o2"])
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")