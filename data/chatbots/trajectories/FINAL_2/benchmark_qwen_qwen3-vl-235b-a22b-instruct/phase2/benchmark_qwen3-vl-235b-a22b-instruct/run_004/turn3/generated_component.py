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
    point_height = 2.0
    
    # Create the base rectangle
    base = gf.components.rectangle(size=(base_width, base_height), layer=layer)
    base_ref = c << base
    base_ref.move((0, 0))  # Position at origin
    
    # Create the four vertical pins
    total_pin_width = 4 * pin_width
    total_spacing = base_width - total_pin_width
    pin_spacing = total_spacing / 5  # Equal spacing between pins and edges
    
    for i in range(4):
        pin_x = pin_spacing + i * (pin_width + pin_spacing)
        pin = gf.components.rectangle(size=(pin_width, pin_height), layer=layer)
        pin_ref = c << pin
        pin_ref.move((pin_x, base_height))  # Position directly on top of base
    
    # Create the bottom point (triangle) - make it sharper and more pointed
    # Use a narrower base for the triangle
    point_base_width = pin_width / 2  # Make it narrower than the pins
    point = gf.components.triangle(x=point_base_width, y=point_height, layer=layer)
    point_ref = c << point
    
    # Position at bottom center, pointing downward
    # Center the triangle under the base
    point_ref.move((base_width/2 - point_base_width/2, -point_height))
    # Rotate 180 degrees to point downward
    point_ref.rotate(180)
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")