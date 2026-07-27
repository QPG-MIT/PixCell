import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    layer = (1, 0)  # Default layer
    
    # Define dimensions based on 25x10μm footprint
    base_width = 25.0
    base_height = 8.0
    pin_width = 2.0
    pin_height = 4.0
    point_height = 3.0
    
    # Create the base rectangle
    base = gf.components.rectangle(size=(base_width, base_height), layer=layer)
    base_ref = c << base
    base_ref.move((0, 0))  # Position at origin
    
    # Create the two vertical pins (tapered, like target image)
    num_pins = 2
    total_pin_width = num_pins * pin_width
    total_spacing = base_width - total_pin_width
    pin_spacing = total_spacing / (num_pins + 1)  # Equal spacing between pins and edges
    
    for i in range(num_pins):
        pin_x = pin_spacing + i * (pin_width + pin_spacing)
        
        # Create a tapered pin using a path that starts wide and ends narrow
        # Define path points for a trapezoid-like pin
        pin_path = gf.Path()
        pin_path.append(gf.path.straight(length=pin_height))
        
        # Define cross-section that tapers from wide at bottom to narrow at top
        # Create a cross-section that tapers
        xs_wide = gf.cross_section.cross_section(width=pin_width, layer=layer)
        xs_narrow = gf.cross_section.cross_section(width=pin_width * 0.4, layer=layer)
        taper_transition = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
        
        # Extrude the path with tapering cross-section
        pin = gf.path.extrude_transition(pin_path, taper_transition)
        pin_ref = c << pin
        pin_ref.move((pin_x, base_height))
        # Pin points upward by default — good for our use case
    
    # Create the bottom point (triangle) - make it sharper and more pointed
    point_base_width = pin_width / 3  # Make it even narrower than before
    point = gf.components.triangle(x=point_base_width, y=point_height, layer=layer)
    point_ref = c << point
    
    # Position at bottom center, pointing downward
    point_ref.move((base_width/2 - point_base_width/2, -point_height))
    # Rotate 180 degrees to point downward
    point_ref.rotate(180)
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")