import gdsfactory as gf

@gf.cell
def custom_device_new_image():
    """
    Recreates the device geometry from the new image using GDSFactory
    parametric primitives and boolean operations.
    The total footprint is estimated to be 3.0 um wide and 5.5 um high.
    """
    c = gf.Component("custom_device_new_image")
    layer = (1, 0)

    # --- 1. Central "I-beam" Structure (bar with holes + connectors) ---

    # Define common parameters for central structure
    bar_height = 0.6
    bar_width = 2.0
    hole_size = 0.3
    # Calculate horizontal distance from the bar's center to the center of each hole.
    # This places holes from x=(-0.5 to -0.2) and x=(0.2 to 0.5)
    hole_dist_from_center = 0.35

    # Create the base rectangular bar, centered at (0,0)
    central_bar_comp = gf.components.rectangle(size=(bar_width, bar_height), centered=True, layer=layer)

    # Create the two square holes, centered and then moved
    hole_left_comp = gf.components.rectangle(size=(hole_size, hole_size), centered=True, layer=layer).copy().movex(-hole_dist_from_center)
    hole_right_comp = gf.components.rectangle(size=(hole_size, hole_size), centered=True, layer=layer).copy().movex(hole_dist_from_center)

    # --- Constructing the Right Connector ---
    # Current_x tracks the rightmost edge of the previously placed segment.
    # It starts at the right edge of the central bar (x = bar_width / 2 = 1.0)
    current_x = bar_width / 2 

    # Segment 1: Short horizontal extension
    seg1_length = 0.1
    rect_ext = gf.components.rectangle(size=(seg1_length, bar_height), centered=True, layer=layer).copy()
    rect_ext.movex(current_x + seg1_length / 2) # Center at 1.0 + 0.05 = 1.05
    current_x += seg1_length # new current_x = 1.1

    # Segment 2: First taper/step out (from width 0.6 to 1.0)
    seg2_length = 0.1
    seg2_width_end = 1.0
    taper_1 = gf.components.taper(length=seg2_length, width1=bar_height, width2=seg2_width_end, layer=layer).copy()
    taper_1.movex(current_x + seg2_length / 2) # Center at 1.1 + 0.05 = 1.15
    current_x += seg2_length # new current_x = 1.2

    # Segment 3: Straight section (width = 1.0)
    seg3_length = 0.1
    rect_mid = gf.components.rectangle(size=(seg3_length, seg2_width_end), centered=True, layer=layer).copy()
    rect_mid.movex(current_x + seg3_length / 2) # Center at 1.2 + 0.05 = 1.25
    current_x += seg3_length # new current_x = 1.3
    
    # Segment 4: Second taper/step out (from width 1.0 to 1.4)
    seg4_length = 0.1
    seg4_width_end = 1.4
    taper_2 = gf.components.taper(length=seg4_length, width1=seg2_width_end, width2=seg4_width_end, layer=layer).copy()
    taper_2.movex(current_x + seg4_length / 2) # Center at 1.3 + 0.05 = 1.35
    current_x += seg4_length # new current_x = 1.4
    
    # Segment 5: Final straight section (width = 1.4)
    seg5_length = 0.1
    rect_end = gf.components.rectangle(size=(seg5_length, seg4_width_end), centered=True, layer=layer).copy()
    rect_end.movex(current_x + seg5_length / 2) # Center at 1.4 + 0.05 = 1.45
    # The rightmost edge of the entire central structure is now at x = 1.5

    # Combine all right-side connector segments using boolean OR.
    right_connector_temp1 = gf.boolean(rect_ext, taper_1, "or", layer=layer)
    right_connector_temp2 = gf.boolean(right_connector_temp1, rect_mid, "or", layer=layer)
    right_connector_temp3 = gf.boolean(right_connector_temp2, taper_2, "or", layer=layer)
    right_connector_solid = gf.boolean(right_connector_temp3, rect_end, "or", layer=layer)

    # Create the left connector by mirroring the right connector.
    left_connector_solid = right_connector_solid.copy().mirror(p1=(0,1), p2=(0,0)) # Mirror across y-axis

    # Combine central bar and both connectors
    i_beam_temp = gf.boolean(central_bar_comp, right_connector_solid, "or", layer=layer)
    i_beam_solid = gf.boolean(i_beam_temp, left_connector_solid, "or", layer=layer)

    # Subtract the holes from the combined I-beam structure
    i_beam_with_holes = gf.boolean(i_beam_solid, hole_left_comp, "not", layer=layer)
    i_beam_with_holes = gf.boolean(i_beam_with_holes, hole_right_comp, "not", layer=layer)
    
    # --- 2. Top Curved "C-shape" Section ---
    # Overall device outer dimensions: 3.0 um wide (x_radius=1.5), 5.5 um high (y_radius=2.75)
    # Connectors' max Y is 0.7. So, the C-shape must start at y=0.7.

    # Removed centered=True
    outer_ellipse = gf.components.ellipse(radii=(1.5, 2.75), layer=layer)
    # Removed centered=True
    inner_ellipse_for_c = gf.components.ellipse(radii=(1.0, 2.0), layer=layer) # Adjusted inner radii

    # Create the raw hollow oval ring for the C-shape
    top_c_shape_raw = gf.boolean(outer_ellipse, inner_ellipse_for_c, "not", layer=layer)

    # Create a cutter to remove the lower part of the C-shape, so it connects to the I-beam.
    # The I-beam's upper edge is at y=0.7. We want to cut everything below this.
    cutter_for_top_c = gf.components.rectangle(size=(5.0, 0.7 - (-3.0)), centered=False, layer=layer).copy()
    cutter_for_top_c.xmin = -2.5 # Arbitrarily wide to cover the whole device horizontally
    cutter_for_top_c.ymin = -3.0 # Position its bottom below the device
    cutter_for_top_c.ymax = 0.7 # Its top edge is at y=0.7

    # Perform the boolean NOT to get the final top C-shape
    top_c_shape = gf.boolean(top_c_shape_raw, cutter_for_top_c, "not", layer=layer)

    # --- 3. Bottom Curved "C-shape" Section ---
    # Mirror the top C-shape across the x-axis (p1=(0,1), p2=(0,0))
    bottom_c_shape = top_c_shape.copy().mirror(p1=(0,1), p2=(0,0))

    # --- 4. Combine all parts into the final device ---
    # Start with the central I-beam with holes
    final_device_temp = gf.boolean(i_beam_with_holes, top_c_shape, "or", layer=layer)
    final_device = gf.boolean(final_device_temp, bottom_c_shape, "or", layer=layer)
    
    # Add the final combined component to the main component 'c'
    c << final_device

    # Optional: Print bounding boxes for debugging
    print(f"I-beam bounds: {i_beam_with_holes.bbox}")
    print(f"Top C-shape bounds: {top_c_shape.bbox}")
    print(f"Bottom C-shape bounds: {bottom_c_shape.bbox}")
    print(f"Final device bounds: {final_device.bbox}")

    return c

# Create the device and save it to a GDS file
if __name__ == "__main__":
    device = custom_device_new_image()
    device.write_gds("custom_device_new_image.gds")
    device.plot() # This line displays the generated GDS in a new window.