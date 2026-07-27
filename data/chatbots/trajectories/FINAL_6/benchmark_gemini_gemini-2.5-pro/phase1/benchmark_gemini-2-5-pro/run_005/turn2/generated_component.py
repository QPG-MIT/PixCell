import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates a central cross shape with four separate square markers floating
    near the tips, matching the new target image.
    """
    # Define a consistent layer for all geometry.
    target_layer = (1, 0)

    # --- Parameters derived from footprint and visual inspection ---
    # Total size for the central cross body.
    cross_size = 4.0

    # Dimensions for the new square markers and their separation.
    square_size = 0.35
    gap = 0.2  # The space between the tip of the petal and the square.

    # --- Derived geometric calculations for the central cross ---
    # The radii are simply half the total size of the cross.
    petal_radius_long = cross_size / 2
    # Estimate the width of the arms.
    arm_width = 1.2
    petal_radius_short = arm_width / 2

    # --- Part 1: Create the central petal cross body (Unchanged) ---
    # Create a tall vertical ellipse and a wide horizontal ellipse.
    ellipse_v = gf.components.ellipse(radii=(petal_radius_short, petal_radius_long), layer=target_layer)
    ellipse_h = gf.components.ellipse(radii=(petal_radius_long, petal_radius_short), layer=target_layer)

    # Combine the two ellipses with a boolean OR (union) to form the petal cross.
    petal_cross = gf.boolean(A=ellipse_v, B=ellipse_h, operation="or", layer=target_layer)

    # --- Part 2: Create and place the four separate square markers ---
    # Create the top-level component that will hold all the shapes.
    c = gf.Component("device_with_markers")

    # Add the central petal_cross as the first shape.
    c.add_ref(petal_cross)

    # Create the square primitive that will be used for the markers.
    marker = gf.components.rectangle(size=(square_size, square_size), layer=target_layer)

    # Calculate the positioning for the markers.
    # Position = ellipse tip + gap + half the marker's size.
    y_pos = petal_radius_long + gap + square_size / 2
    x_pos = petal_radius_long + gap + square_size / 2

    # Add the four markers as separate references, positioned correctly.
    c.add_ref(marker).movey(y_pos)  # Top
    c.add_ref(marker).movey(-y_pos) # Bottom
    c.add_ref(marker).movex(x_pos)  # Right
    c.add_ref(marker).movex(-x_pos) # Left

    # The final component now contains 5 separate polygons.
    return c

# --- Main execution block ---
# This part of the script runs only when the file is executed directly.
if __name__ == "__main__":
    # Create an instance of the component by calling the function.
    device_to_save = create_device()
    
    # Write the component to a GDSII file.
    device_to_save.write_gds("device.gds")

    # Optionally, show the component in a viewer if you want to see it.
    # device_to_save.show()