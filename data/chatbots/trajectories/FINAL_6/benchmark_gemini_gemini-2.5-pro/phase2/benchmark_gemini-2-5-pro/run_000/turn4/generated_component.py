import gdsfactory as gf
import numpy as np

@gf.cell
def lobed_cross():
    """
    Creates a four-lobed cross shape using a boolean composition strategy.

    This improved design strategy addresses the geometric inaccuracies of the
    previous version (ellipse + rectangle). It builds a single, continuous arm
    by combining shapes with boolean operations and then replicates it with C4
    rotational symmetry.

    1.  **Petal Creation (Intersection):** A single "petal" with sharp tips is
        first created. This is achieved by taking the boolean INTERSECTION ('and')
        of two overlapping circles. This method precisely forms the desired
        lens-like shape that is pointed at both ends.
    2.  **Arm Creation (Union):** The created petal is combined with a
        rectangular "stem" using a boolean UNION ('or'). This merges the two
        shapes into a single, seamless polygon representing one complete arm of
        the cross. This arm is designed to extend upwards in the +y direction
        from the origin (0, 0).
    3.  **Final Assembly (Rotation):** The main component creates four instances
        of this unified arm. Each instance is rotated by a multiple of 90
        degrees (0, 90, 180, 270) around the origin to form the complete,
        symmetric cross, ensuring the lobes meet cleanly at a single central point.
    """
    # --- 1. Define Parameters to meet 4.7x4.7 um footprint ---
    footprint = 4.7
    arm_total_length = footprint / 2.0  # 2.35 um

    # Define the proportions of the arm
    stem_length = 0.5
    stem_width = 0.3
    petal_length = arm_total_length - stem_length  # 1.85 um
    petal_max_width = 1.7  # Desired max width of the lobe

    # Calculate circle parameters needed to create a lens of the desired dimensions
    # via boolean intersection.
    # length = 2 * sqrt(R^2 - x_offset^2)
    # width = 2 * (R - x_offset)
    # Solving these equations for R and x_offset:
    R = (petal_length**2 + petal_max_width**2) / (4 * petal_max_width)
    x_offset = R - (petal_max_width / 2)

    # --- 2. Create a Single Unified Arm via Boolean Ops ---
    # This is defined in a nested function to keep the logic modular.
    @gf.cell
    def create_single_arm():
        # Component to hold the final unified arm
        arm_component = gf.Component("unified_arm")

        # a. Create the petal via intersection of two circles
        petal_source = gf.Component("petal_source_geometry")
        c1 = petal_source << gf.components.circle(radius=R, layer=(1, 0))
        c2 = petal_source << gf.components.circle(radius=R, layer=(1, 0))
        c1.movex(x_offset)
        c2.movex(-x_offset)
        petal = gf.boolean(c1, c2, operation="and", layer=(1, 0))

        # b. Create the stem
        stem = gf.components.rectangle(size=(stem_width, stem_length), layer=(1, 0))

        # c. Position petal and stem for union
        # Add references to the final arm component
        petal_ref = arm_component << petal
        stem_ref = arm_component << stem
        
        # Rotate the horizontally-created petal to be vertical
        petal_ref.rotate(90)
        # Move it so its bottom tip is at the origin
        petal_ref.ymin = 0

        # Move the stem to sit on top of the petal
        stem_ref.movey(petal_length)

        # d. Union the petal and stem into one shape
        final_arm = gf.boolean(petal_ref, stem_ref, operation="or", layer=(1, 0))
        return final_arm

    # --- 3. Assemble the Final Cross from Four Arms ---
    c = gf.Component("final_lobed_cross")

    # Create the single arm template
    arm_template = create_single_arm()

    # Create and rotate four references to the arm template
    arm_top = c << arm_template
    arm_right = c << arm_template
    arm_bottom = c << arm_template
    arm_left = c << arm_template

    # Rotate the arms into their final positions around the origin.
    # Rotations are counter-clockwise.
    arm_top.rotate(0)
    arm_right.rotate(270)  # or -90
    arm_bottom.rotate(180)
    arm_left.rotate(90)

    return c

# To display and SAVE the component if the script is run directly
if __name__ == "__main__":
    # Instantiate the component
    device = lobed_cross()

    # Display the component in the KLayout viewer (optional, for verification)
    device.show()

    # Save the component to a GDSII file.
    device.write_gds("lobed_cross.gds")
    print("GDS file 'lobed_cross.gds' saved successfully.")