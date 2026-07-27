import gdsfactory as gf
import numpy as np

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Device footprint parameters
    TOTAL_WIDTH = 120.0  # microns
    TOTAL_HEIGHT = 4.0   # microns

    # Parameters for the lines and gaps
    LINE_WIDTH = 0.5  # microns, width of each black line
    
    # Calculate GAP_WIDTH based on total height and number of lines/gaps
    # Total height = 4 * LINE_WIDTH + 3 * GAP_WIDTH
    # 4.0 = 4 * 0.5 + 3 * GAP_WIDTH
    # 4.0 = 2.0 + 3 * GAP_WIDTH
    # 2.0 = 3 * GAP_WIDTH
    GAP_WIDTH = 2.0 / 3.0 # microns, width of each white gap

    # 1. Create the outermost black shape (a rounded rectangle)
    outer_radius = TOTAL_HEIGHT / 2 # 2.0 um
    rect_length_outer = TOTAL_WIDTH - 2 * outer_radius # 120 - 4 = 116 um
    
    # Create the central rectangular portion of the outer shape (centered at 0,0)
    rect_mid_outer_comp = gf.components.rectangle(
        size=(rect_length_outer, TOTAL_HEIGHT), 
        layer=(1, 0), 
        centered=True
    )

    # Create a base circle component that will be used for the ends
    base_outer_circle = gf.components.circle(radius=outer_radius, layer=(1, 0))

    # Create distinct components for the left and right circles, positioned correctly.
    # Each will contain a reference to the 'base_outer_circle', and that reference will be moved.
    left_outer_circle_positioned = gf.Component("left_outer_circle_positioned")
    left_outer_circle_positioned_ref = left_outer_circle_positioned << base_outer_circle
    left_outer_circle_positioned_ref.move((-rect_length_outer / 2, 0))

    right_outer_circle_positioned = gf.Component("right_outer_circle_positioned")
    right_outer_circle_positioned_ref = right_outer_circle_positioned << base_outer_circle
    right_outer_circle_positioned_ref.move((rect_length_outer / 2, 0))

    # Combine them using boolean OR to form the complete outer rounded shape.
    # gf.boolean can take a list of components/references for multi-operand operations.
    # FIX: Added 'layer=(1, 0)'
    outer_shape = gf.boolean(
        [rect_mid_outer_comp, left_outer_circle_positioned, right_outer_circle_positioned], 
        "or",
        layer=(1, 0) 
    )

    # 2. Create the three internal white gaps (also rounded rectangles)
    gap_rounding_radius = GAP_WIDTH / 2 # (2/3) / 2 = 1/3 um
    rect_length_gap = TOTAL_WIDTH - 2 * gap_rounding_radius # 120 - 2*(1/3) = 120 - 2/3 um

    # Calculate the y-centers for the three gaps
    # The overall stack is centered on y=0, so the vertical extent is [-2.0, 2.0].
    # y-center for the first gap (from bottom)
    y_center_gap1 = -TOTAL_HEIGHT / 2 + LINE_WIDTH + GAP_WIDTH / 2
    # y-center for the second gap
    y_center_gap2 = y_center_gap1 + LINE_WIDTH + GAP_WIDTH
    # y-center for the third gap
    y_center_gap3 = y_center_gap2 + LINE_WIDTH + GAP_WIDTH

    # Helper function to create a single rounded gap component, positioned at its y_center.
    # This function returns a Component whose internal geometry is already shifted.
    def create_rounded_gap_component(y_center, layer=(1,0)): # Use layer (1,0) for the internal shapes for consistency too, since they will be subtracted.
        gap_comp_name = f"rounded_gap_y{y_center:.4f}"
        rounded_gap_c = gf.Component(gap_comp_name)

        # Central rectangle for the gap (centered at (0,0) initially for its own definition)
        gap_rect_comp = gf.components.rectangle(
            size=(rect_length_gap, GAP_WIDTH), 
            layer=layer, 
            centered=True
        )

        # Base circle for gap ends (definition itself won't be moved)
        base_gap_circle = gf.components.circle(radius=gap_rounding_radius, layer=layer)
        
        # Left gap circle positioned (within its own temporary component)
        left_gap_circle_pos_comp = gf.Component(f"{gap_comp_name}_left_circle")
        left_gap_circle_pos_comp_ref = left_gap_circle_pos_comp << base_gap_circle
        left_gap_circle_pos_comp_ref.move((-rect_length_gap / 2, 0))

        # Right gap circle positioned (within its own temporary component)
        right_gap_circle_pos_comp = gf.Component(f"{gap_comp_name}_right_circle")
        right_gap_circle_pos_comp_ref = right_gap_circle_pos_comp << base_gap_circle
        right_gap_circle_pos_comp_ref.move((rect_length_gap / 2, 0))
        
        # Combine them to form the rounded gap shape (still centered at (0,0) for this combined shape)
        # FIX: Added 'layer' argument here as well for the internal boolean
        temp_gap_shape_at_origin = gf.boolean(
            [gap_rect_comp, left_gap_circle_pos_comp, right_gap_circle_pos_comp], 
            "or",
            layer=layer
        )
        
        # Add the combined gap shape to the final component for this specific gap, and move it to y_center.
        # This reference is inside 'rounded_gap_c'
        final_gap_ref = rounded_gap_c << temp_gap_shape_at_origin
        final_gap_ref.move((0, y_center))

        return rounded_gap_c # Return the component that is now fully positioned

    # Create the three rounded gap shapes, which are now correctly positioned components.
    gap1_comp = create_rounded_gap_component(y_center_gap1, layer=(1,0))
    gap2_comp = create_rounded_gap_component(y_center_gap2, layer=(1,0))
    gap3_comp = create_rounded_gap_component(y_center_gap3, layer=(1,0))

    # 3. Perform boolean subtractions to cut the gaps from the outer shape.
    # FIX: Added 'layer=(1, 0)' to all subtraction calls.
    final_shape = gf.boolean(outer_shape, gap1_comp, "not", layer=(1, 0))
    final_shape = gf.boolean(final_shape, gap2_comp, "not", layer=(1, 0))
    final_shape = gf.boolean(final_shape, gap3_comp, "not", layer=(1, 0))
    
    # Add the final result to the main component `c`
    c << final_shape

    return c

# Create the device and save it
if __name__ == "__main__":
    device = my_device()
    device.show() # Display the component in KLayout if available
    # device.write_gds("my_device.gds")