import gdsfactory as gf

@gf.cell
def create_flower_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Parameters based on 4.7um footprint
    petal_length = 1.6  # Length of each petal from center to end
    petal_width = 0.8   # Width of each petal
    straight_extension = 0.4  # Straight section at end of each petal
    
    # Create a cross-section for the petal
    xs = gf.cross_section.cross_section(width=petal_width, layer=layer)
    
    # Create one petal using a path with smooth curves
    # Create a straight path for the extension
    straight_path = gf.path.straight(length=straight_extension)
    
    # Create an euler bend path for the curved part
    curve_path = gf.path.euler(radius=petal_length/2, angle=60, p=0.5)
    curve_path += gf.path.euler(radius=petal_length/2, angle=-60, p=0.5)
    
    # Combine the paths
    full_path = straight_path + curve_path
    
    # Create the petal component by extruding the path
    petal_component = gf.Component()
    petal_shape = gf.path.extrude(full_path, cross_section=xs)
    petal_ref = petal_component << petal_shape
    
    # Now create the full device by rotating and placing 4 copies
    petal_ref_0 = c << petal_component
    petal_ref_0.rotate(0)  # Right
    
    petal_ref_90 = c << petal_component
    petal_ref_90.rotate(90)  # Up
    
    petal_ref_180 = c << petal_component
    petal_ref_180.rotate(180)  # Left
    
    petal_ref_270 = c << petal_component
    petal_ref_270.rotate(270)  # Down
    
    # Center the device
    bbox = c.bbox
    center_x = (bbox[0][0] + bbox[1][0]) / 2
    center_y = (bbox[0][1] + bbox[1][1]) / 2
    
    # Move all components to center the device
    for ref in c.references:
        ref.move((-center_x, -center_y))
    
    # Add ports for each arm
    c.add_port("o1", center=(petal_length, 0), width=petal_width, orientation=0)
    c.add_port("o2", center=(0, petal_length), width=petal_width, orientation=90)
    c.add_port("o3", center=(-petal_length, 0), width=petal_width, orientation=180)
    c.add_port("o4", center=(0, -petal_length), width=petal_width, orientation=270)
    
    return c

# Create and save the device
device = create_flower_device()
device.write_gds("flower_device.gds")