import gdsfactory as gf

@gf.cell
def create_device_geometry():
    """
    Recreates the device geometry from the image.
    Footprint: 4.7um x 4.7um
    Method: Boolean union of two ellipses and a cross.
    """
    c = gf.Component("device_recreation")
    layer = (1, 0)
    
    # --- Dimensions ---
    # The total footprint is 4.7um. The pins must reach this limit.
    footprint_size = 4.7
    pin_thickness = 0.28
    
    # The 'petals' are slightly shorter than the pins to match the image.
    petal_length = 3.9
    petal_width = 1.3
    
    # 1. Create the petals using two ellipses
    # Horizontal ellipse
    e_horiz = gf.components.ellipse(radii=(petal_length / 2, petal_width / 2), layer=layer)
    # Vertical ellipse
    e_vert = gf.components.ellipse(radii=(petal_width / 2, petal_length / 2), layer=layer)
    
    # 2. Create the terminal pins using a cross primitive
    # This ensures the footprint is exactly 4.7um x 4.7um
    pins = gf.components.cross(length=footprint_size, width=pin_thickness, layer=layer)
    
    # 3. Perform Boolean Union (OR) to create a single manifold shape
    # Combine horizontal and vertical ellipses
    petals_union = gf.boolean(A=e_horiz, B=e_vert, operation="or", layer=layer)
    
    # Combine the petals with the pin cross
    final_shape = gf.boolean(A=petals_union, B=pins, operation="or", layer=layer)
    
    # Add the final geometry to the component
    c << final_shape
    
    return c

if __name__ == "__main__":
    # Generate the component
    component = create_device_geometry()
    
    # Define the output filename
    output_filename = "recreated_device.gds"
    
    # Write the GDS file to the current directory
    component.write_gds(output_filename)
    
    print(f"Success: GDS file '{output_filename}' has been created.")