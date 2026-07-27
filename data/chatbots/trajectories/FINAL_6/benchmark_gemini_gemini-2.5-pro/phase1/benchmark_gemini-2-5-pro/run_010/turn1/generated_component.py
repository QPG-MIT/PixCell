import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the four-petaled cross shape using boolean operations on primitives.
    
    The shape is constructed by taking the union of three components:
    1. A base cross that defines the overall footprint and the rectangular tips.
    2. A horizontally oriented ellipse to create the horizontal bulges.
    3. A vertically oriented ellipse to create the vertical bulges.
    """
    # 1. Define parameters based on the 4.7x4.7 um footprint and visual inspection.
    footprint_dim = 4.7
    target_layer = (1, 0)
    
    # The cross defines the overall size and the width of the arm tips.
    cross_length = footprint_dim
    # The width of the rectangular part of the arm is estimated visually.
    cross_width = 0.5
    
    # The ellipses create the central bulge. Their major radius must be less
    # than half the footprint to ensure the bulge is contained within the arms.
    ellipse_major_radius = 2.1
    # The minor radius determines the "fatness" of the petals.
    ellipse_minor_radius = 1.1

    # 2. Create the primitive components on the target layer.
    
    # Create the base cross structure.
    base_cross = gf.components.cross(
        length=cross_length, width=cross_width, layer=target_layer
    )
    
    # Create the two ellipses that will be unioned to form the petal shape.
    ellipse_horizontal = gf.components.ellipse(
        radii=(ellipse_major_radius, ellipse_minor_radius), layer=target_layer
    )
    ellipse_vertical = gf.components.ellipse(
        radii=(ellipse_minor_radius, ellipse_major_radius), layer=target_layer
    )

    # 3. Perform boolean operations to combine the shapes, specifying the output layer.
    
    # First, union the two ellipses to create the four-petaled core.
    petals = gf.boolean(
        A=ellipse_horizontal, 
        B=ellipse_vertical, 
        operation="or",
        layer=target_layer
    )
    
    # Finally, union the base cross with the petal shape.
    final_shape = gf.boolean(
        A=base_cross, 
        B=petals, 
        operation="or",
        layer=target_layer
    )
    
    # 4. Create the final component and add the resulting geometry as a reference.
    c = gf.Component()
    c << final_shape
    
    return c

# Instantiate the component to verify its creation and size.
# This part is for testing and visualization, not part of the required function.
if __name__ == "__main__":
    device = create_device()
    # Corrected the line below by removing the unsupported 'show_ports' argument.
    device.show()
    
    # Verify that the component size matches the footprint constraint.
    print(f"Component created: {device.name}")
    print(f"Footprint (width, height): ({device.size[0]:.2f}, {device.size[1]:.2f}) µm")