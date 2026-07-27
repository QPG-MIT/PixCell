import gdsfactory as gf
import numpy as np

@gf.cell
def lobed_cross():
    """
    Creates a four-lobed cross shape by refining a boolean composition strategy.

    This version corrects the geometric inaccuracies of the previous attempt. The
    prior code produced nearly circular lobes because the specified length and
    width of the "petal" were almost equal. This version adjusts the parameters
    to create the correct, slender, lens-like shape for each lobe, matching the
    target image.

    The construction process remains:
    1.  **Petal Creation (Intersection):** A single, pointed "petal" is formed
        by the boolean intersection of two carefully calculated circles. The new
        parameters ensure the resulting lens shape has the correct aspect ratio.
    2.  **Arm Creation (Union):** The petal is merged with a rectangular "stem"
        using a boolean union, creating one complete, seamless arm.
    3.  **Final Assembly (Rotation):** Four instances of the arm are rotated
        (0, 90, 180, 270 degrees) around the origin. This C4 symmetry ensures
        the lobes meet perfectly at a sharp central point.
    """
    # --- 1. Define Parameters to match Target Proportions and Footprint ---
    footprint = 4.7
    arm_total_length = footprint / 2.0  # 2.35 um

    # Adjust the proportions of the arm to match the target image
    stem_length = 0.4
    stem_width = 0.35
    # The petal is the remaining length of the arm
    petal_length = arm_total_length - stem_length  # 2.35 - 0.4 = 1.95 um
    
    # CRITICAL CHANGE: Reduce max width to create a slender, lens-like shape
    # instead of a circular one.
    petal_max_width = 1.2  # Previous value (1.7) was too close to length (1.85)

    # Recalculate circle parameters for the boolean intersection based on
    # the desired final dimensions of the lens-shaped petal.
    # R: Radius of the two source circles
    # x_offset: ateral shift of each circle's center from the origin
    R = (petal_length**2 + petal_max_width**2) / (4 * petal_max_width)
    x_offset = R - (petal_max_width / 2)

    # --- 2. Create a Single Unified Arm (Petal + Stem) ---
    # This is encapsulated in a nested function for modularity.
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

        # c. Position petal and stem for the union operation
        petal_ref = arm_component << petal
        stem_ref = arm_component << stem
        
        # The petal is created horizontally; rotate it to be vertical
        petal_ref.rotate(90)
        # Move the petal so its bottom tip (the sharp point) is at the origin (0, 0)
        petal_ref.ymin = 0

        # Move the stem's center to the y-coordinate of the petal's outer tip.
        # This creates a significant, robust overlap for the boolean union.
        stem_ref.movey(petal_length)

        # d. Union the positioned petal and stem into a single, continuous polygon
        final_arm = gf.boolean(petal_ref, stem_ref, operation="or", layer=(1, 0))
        return final_arm

    # --- 3. Assemble the Final Cross from Four Rotated Arms ---
    c = gf.Component("final_lobed_cross")

    # Create the single arm component which will be used as a template
    arm_template = create_single_arm()

    # Create four references to the arm template
    arm_top = c << arm_template
    arm_right = c << arm_template
    arm_bottom = c << arm_template
    arm_left = c << arm_template

    # Rotate the arms into their final positions around the origin.
    arm_top.rotate(0)      # Pointing up (+y)
    arm_right.rotate(270)  # Pointing right (+x)
    arm_bottom.rotate(180) # Pointing down (-y)
    arm_left.rotate(90)    # Pointing left (-x)

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