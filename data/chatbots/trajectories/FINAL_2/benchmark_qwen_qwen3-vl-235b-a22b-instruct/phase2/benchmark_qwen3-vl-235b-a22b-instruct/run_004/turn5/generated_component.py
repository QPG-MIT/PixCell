import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    layer = (1, 0)  # Default layer
    
    # Define dimensions based on 25x10μm footprint
    # For the target image, we want a more vertical orientation
    base_width = 10.0  # Width is now smaller
    base_height = 25.0  # Height is now larger to match target
    pin_width = 2.0
    pin_height = 8.0
    point_height = 3.0
    
    # Create the base rectangle (taller than wide to match target)
    base = gf.components.rectangle(size=(base_width, base_height), layer=layer)
    base_ref = c << base
    base_ref.move((0, 0))  # Position at origin
    
    # Create a single tapered pin on the top right corner (matching target)
    # Create a tapered pin using a path that starts wide and ends narrow
    pin_path = gf.Path()
    pin_path.append(gf.path.straight(length=pin_height))
    
    # Define cross-section that tapers from wide at bottom to narrow at top
    xs_wide = gf.cross_section.cross_section(width=pin_width, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=pin_width * 0.2, layer=layer)  # Make it even narrower for sharper point
    taper_transition = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    
    # Extrude the path with tapering cross-section
    pin = gf.path.extrude_transition(pin_path, taper_transition)
    pin_ref = c << pin
    
    # Position at top right corner, pointing upward
    pin_ref.move((base_width - pin_width, base_height))
    
    # Create the bottom point (triangle) - make it sharper and more pointed
    point_base_width = pin_width * 0.3  # Make it very narrow
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