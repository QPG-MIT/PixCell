import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates a cross shape composed of four petals with rectangular stems,
    matching the target image. This is achieved by creating a central
    petal body and a stem cross, then merging them with a boolean union.
    """
    # Define a consistent layer for all geometry.
    target_layer = (1, 0)

    # --- Parameters derived from footprint and visual inspection ---
    # The total extent of the final device including stems.
    footprint_size = 4.7
    # The size of the central "petal" body, excluding the stems.
    petal_body_size = 4.0
    # The width of the arms of the petal body.
    petal_arm_width = 1.2
    # The width of the rectangular stems.
    stem_width = 0.4

    # --- Part 1: Create the central petal body ---
    # This part creates a smooth, four-petal shape from two overlapping ellipses.
    petal_radius_long = petal_body_size / 2
    petal_radius_short = petal_arm_width / 2
    
    ellipse_v = gf.components.ellipse(
        radii=(petal_radius_short, petal_radius_long), layer=target_layer
    )
    ellipse_h = gf.components.ellipse(
        radii=(petal_radius_long, petal_radius_short), layer=target_layer
    )
    
    # Union the two ellipses to form the curved petal cross.
    petal_cross = gf.boolean(
        A=ellipse_v, B=ellipse_h, operation="or", layer=target_layer
    )

    # --- Part 2: Create the stems using a cross primitive ---
    # This creates the rectangular arms that extend to the full footprint.
    stem_cross = gf.components.cross(
        length=footprint_size, width=stem_width, layer=target_layer
    )

    # --- Part 3: Combine the petal body and the stems ---
    # A final boolean "or" (union) operation merges the two shapes into one
    # continuous polygon that matches the target device.
    final_device = gf.boolean(
        A=petal_cross, B=stem_cross, operation="or", layer=target_layer
    )

    return final_device

# --- Main execution block ---
# This part of the script runs only when the file is executed directly.
if __name__ == "__main__":
    # Create an instance of the component by calling the function.
    device_to_save = create_device()
    
    # Write the component to a GDSII file.
    device_to_save.write_gds("device.gds")

    # Optionally, show the component in a viewer if you want to see it.
    # device_to_save.show()