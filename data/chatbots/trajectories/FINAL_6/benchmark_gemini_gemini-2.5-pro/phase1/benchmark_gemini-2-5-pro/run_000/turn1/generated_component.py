import gdsfactory as gf

@gf.cell
def patterned_cross():
    """
    Creates a four-petal cross shape using boolean operations on parametric primitives.

    The geometry is constructed by the union of two "dumbbell" shapes, one oriented
    vertically and the other horizontally. Each dumbbell consists of a central
    ellipse and two rectangular tips at its ends.

    The dimensions are parametrically derived to precisely match the specified
    total footprint of 4.7x4.7 micrometers.
    """

    # --- 1. Define Dimensions from Footprint ---
    # The device footprint is 4.7 x 4.7 um.
    total_dim = 4.7
    half_dim = total_dim / 2.0

    # Estimate the dimensions of the rectangular tips based on visual inspection.
    tip_length = 0.4  # Length of the rectangle along the dumbbell's main axis
    tip_width = 0.3   # Width of the rectangle perpendicular to the main axis

    # Correctly calculate the ellipse's major radius.
    # The total extent of an arm (half_dim) is the sum of the ellipse's major
    # radius and half the length of the rectangular tip.
    # So, radius_major + tip_length / 2 = half_dim
    radius_major = half_dim - (tip_length / 2.0)  # e.g., 2.35 - 0.2 = 2.15 um

    # The minor radius of the ellipse defines the "fatness" of the petals.
    # This is estimated visually.
    radius_minor = 0.5

    # --- 2. Create the Vertical Dumbbell Component ---
    # This component will form the vertical part of the final cross.
    dumbbell_v = gf.Component("vertical_dumbbell")

    # Add a vertically oriented central ellipse.
    dumbbell_v << gf.components.ellipse(radii=(radius_minor, radius_major), layer=(1, 0))

    # Create a single tip component. The rectangle is centered by default.
    tip = gf.components.rectangle(size=(tip_width, tip_length), layer=(1, 0))

    # Add the top and bottom rectangular tips as references.
    tip_top = dumbbell_v << tip
    tip_bottom = dumbbell_v << tip

    # Position the tips to overlap with the ends of the ellipse.
    # We move the center of the tip to the end of the ellipse's major axis.
    tip_top.movey(radius_major)
    tip_bottom.movey(-radius_major)

    # --- 3. Create the Horizontal Dumbbell Component ---
    # This component will form the horizontal part.
    dumbbell_h = gf.Component("horizontal_dumbbell")

    # Add a horizontally oriented central ellipse (by swapping radii).
    dumbbell_h << gf.components.ellipse(radii=(radius_major, radius_minor), layer=(1, 0))

    # Create a tip for the horizontal arms.
    tip_h = gf.components.rectangle(size=(tip_length, tip_width), layer=(1, 0))

    # Add the left and right tips as references.
    tip_left = dumbbell_h << tip_h
    tip_right = dumbbell_h << tip_h

    # Position the tips to overlap with the ends of the horizontal ellipse.
    tip_left.movex(-radius_major)
    tip_right.movex(radius_major)

    # --- 4. Combine with a Boolean Union Operation ---
    # The final shape is the union ("or") of the two dumbbell components.
    # gf.boolean returns a new component containing the merged geometry.
    final_device = gf.boolean(
        A=dumbbell_v,
        B=dumbbell_h,
        operation="or",
        layer=(1, 0)
    )

    return final_device

# To display and SAVE the component if the script is run directly
if __name__ == "__main__":
    # Instantiate the component
    c = patterned_cross()

    # Display the component in the KLayout viewer (optional, for verification)
    c.show()

    # FIX: Save the component to a GDSII file. This command is required to
    # produce an output file.
    c.write_gds("patterned_cross.gds")
    print("GDS file 'patterned_cross.gds' saved successfully.")