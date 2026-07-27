import gdsfactory as gf

@gf.cell
def get_stadium_frame():
    """Constructs the stadium-shaped frame using path extrusion."""
    # Define parameters based on the 3.0 x 5.5 footprint
    # Frame width is approx 0.3um based on standard waveguide sizes
    width = 3.0
    height = 5.5
    radius = 1.0 # Radius of the bends
    
    # Path construction for a stadium (Straight -> Bend -> Straight -> Bend)
    # This creates a closed loop frame
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    
    path = gf.Path()
    # Path traces the center of the frame
    path.append(gf.path.straight(length=height - 2 * radius))
    path.append(gf.path.arc(radius=radius, angle=90))
    path.append(gf.path.straight(length=width - 2 * radius))
    path.append(gf.path.arc(radius=radius, angle=90))
    path.append(gf.path.straight(length=height - 2 * radius))
    path.append(gf.path.arc(radius=radius, angle=90))
    path.append(gf.path.straight(length=width - 2 * radius))
    path.append(gf.path.arc(radius=radius, angle=90))
    
    # Extrude the path into a component
    frame = gf.path.extrude(path, cross_section=xs)
    c << frame
    return c

@gf.cell
def get_inner_bars():
    """Constructs the two inner bars as references."""
    c = gf.Component()
    
    # Create the rectangles as separate references
    bar1 = c << gf.components.rectangle(size=(1.5, 0.3), layer=(1, 0))
    bar2 = c << gf.components.rectangle(size=(1.5, 0.3), layer=(1, 0))
    
    # Position them relatively
    bar1.movey(0.7)
    bar2.movey(-0.7)
    
    return c

@gf.cell
def chain_link_device():
    """Combines frame and bars using Boolean OR operation."""
    c = gf.Component()
    
    # Generate the sub-components
    frame_ref = get_stadium_frame()
    bars_ref = get_inner_bars()
    
    # Perform Boolean OR to merge the geometries into one solid layer
    # This welds the bars to the frame
    merged_device = gf.boolean(frame_ref, bars_ref, operation="or", layer=(1, 0))
    
    # Add the result to the main component
    c << merged_device
    
    return c

if __name__ == "__main__":
    # 1. Create the device
    device = chain_link_device()
    
    # 2. Save the GDS file
    device.write_gds("chain_link_device.gds")
    
    # 3. Visualize
    device.show()
    print("GDS file 'chain_link_device.gds' produced successfully.")