import gdsfactory as gf

# Define a default layer for all geometries
LAYER = (1, 0)

@gf.cell
def custom_device(
    radius: float = 1.5, # Default radius to fit a 3.0um diameter within a 3.0 x 5.5 footprint
    layer: tuple = LAYER
) -> gf.Component:
    """
    Creates a simple black circle.
    """
    c = gf.Component("simple_black_circle")

    # Create the circular shape
    circle_comp = gf.components.circle(
        radius=radius,
        layer=layer
    )
    
    # Add the circle to the component and center it at the origin
    c.add_ref(circle_comp).center = (0, 0)
    
    return c

# Define the radius value to be used for the circle
circle_radius = 1.5 

# Create the device, passing the defined radius
device = custom_device(radius=circle_radius)

# Save the device to a GDS file
device.write_gds("simple_black_circle.gds")

# Print the computed footprint
computed_width = device.xsize
computed_height = device.ysize

print(f"Computed device width: {computed_width:.3f} um")
print(f"Computed device height: {computed_height:.3f} um")
print(f"Expected footprint_um (from previous context, for reference): [3.0, 5.5]")
# Now using the globally defined 'circle_radius' variable
print(f"Note: This script generates a perfect circle with diameter {circle_radius * 2:.1f} um.")