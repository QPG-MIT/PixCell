import gdsfactory as gf
import numpy as np

@gf.cell
def my_device():
    c = gf.Component()
    
    # Define parameters based on footprint and image analysis
    total_width = 120.0
    total_height = 4.0
    
    # Unit width for lines and gaps
    unit_width = total_height / 9 
    gap_width = unit_width
    
    # Layer for the device geometry
    device_layer = (1, 0)
    
    # 1. Create the main solid black rectangle (the canvas)
    main_rect_ref = c << gf.components.rectangle(
        size=(total_width, total_height), 
        layer=device_layer, 
        centered=True
    )
    
    # Parameters for the white channel construction
    W_edge_bar_white = gap_width # Width of the vertical white bars at the edges
    R_bend = 1.0 # Radius for the Euler bends (visually estimated)
    
    # Corrected: Define cross-section for the white cutouts,
    # allowing for smaller bend radius by setting radius_min
    cutout_xs = gf.cross_section.cross_section(width=gap_width, layer=device_layer, radius_min=R_bend)
    
    # Y-centers for the 4 white channels (derived in the thought process)
    # [4/3, 4/9, -4/9, -4/3] um
    channel_y_centers = [4/3, 4/9, -4/9, -4/3]
    
    # A temporary component to aggregate all white cutouts for boolean subtraction
    white_cutouts_aggr = gf.Component("white_cutouts")

    # Add the two main vertical white bars at the edges
    left_bar_ref = white_cutouts_aggr << gf.components.rectangle(
        size=(W_edge_bar_white, total_height), 
        layer=device_layer, 
        centered=True
    )
    left_bar_ref.movex(-total_width/2 + W_edge_bar_white/2)
    
    right_bar_ref = white_cutouts_aggr << gf.components.rectangle(
        size=(W_edge_bar_white, total_height), 
        layer=device_layer, 
        centered=True
    )
    right_bar_ref.movex(total_width/2 - W_edge_bar_white/2)

    # Calculate horizontal length of the straight middle segment for channels
    # Each bend_euler consumes R_bend horizontally and R_bend vertically if angle=90.
    # The straight segment starts after the left edge bar and the left bend's horizontal span.
    # It ends before the right bend's horizontal span and the right edge bar.
    L_horiz_straight_channel = total_width - 2 * W_edge_bar_white - 2 * R_bend
    
    # For each of the four channels, construct its shape
    for y_center in channel_y_centers:
        # 1. Central straight horizontal segment
        straight_middle_ref = white_cutouts_aggr << gf.components.straight(
            length=L_horiz_straight_channel, 
            cross_section=cutout_xs
        )
        # Position this segment in the middle of the non-bar area
        straight_middle_ref.movex(-total_width/2 + W_edge_bar_white + R_bend + L_horiz_straight_channel / 2)
        straight_middle_ref.movey(y_center)
        
        # Determine bend angles and vertical connection lengths based on y_center
        if y_center > 0: # Top half channels (bends curve UP then DOWN)
            left_bend_angle = 90  # Horizontal (o1) to Vertical-up (o2)
            right_bend_angle = -90 # Horizontal (o1) to Vertical-down (o2)
            # Length to connect from bend's vertical output to the top/bottom edge
            L_connect_vert_left = total_height / 2 - (y_center + R_bend)
            L_connect_vert_right = (y_center - R_bend) - (-total_height / 2)
        else: # Bottom half channels (bends curve DOWN then UP)
            left_bend_angle = -90 # Horizontal (o1) to Vertical-down (o2)
            right_bend_angle = 90  # Horizontal (o1) to Vertical-up (o2)
            # Length to connect from bend's vertical output to the top/bottom edge
            L_connect_vert_left = (y_center - R_bend) - (-total_height / 2)
            L_connect_vert_right = total_height / 2 - (y_center + R_bend)

        # 2. Left Bend Component
        bend_left_comp = gf.components.bend_euler(
            radius=R_bend, 
            angle=left_bend_angle, 
            cross_section=cutout_xs
        )
        bend_left_ref = white_cutouts_aggr << bend_left_comp
        # Connect bend's horizontal input to the straight middle segment's left port
        bend_left_ref.connect("o1", straight_middle_ref.ports["o1"])

        # 3. Right Bend Component
        bend_right_comp = gf.components.bend_euler(
            radius=R_bend, 
            angle=right_bend_angle, 
            cross_section=cutout_xs
        )
        bend_right_ref = white_cutouts_aggr << bend_right_comp
        # Connect bend's horizontal input to the straight middle segment's right port
        bend_right_ref.connect("o1", straight_middle_ref.ports["o2"])

        # 4. Vertical Connection Segments (from bends to device edges)
        # Left side vertical connection
        if L_connect_vert_left > 1e-3: # Only add if length is significant
            vert_connect_left_ref = white_cutouts_aggr << gf.components.straight(
                length=L_connect_vert_left, 
                cross_section=cutout_xs
            )
            # Connect the vertical straight to the bend's vertical output port
            # The 'o2' port of bend_left_ref always points away from the bend's center, in the vertical direction.
            # We want to connect the 'o1' of the straight to this 'o2' to extend it.
            vert_connect_left_ref.connect("o1", bend_left_ref.ports["o2"])

        # Right side vertical connection
        if L_connect_vert_right > 1e-3: # Only add if length is significant
            vert_connect_right_ref = white_cutouts_aggr << gf.components.straight(
                length=L_connect_vert_right, 
                cross_section=cutout_xs
            )
            # Connect the vertical straight to the bend's vertical output port
            vert_connect_right_ref.connect("o1", bend_right_ref.ports["o2"])

    # 5. Perform boolean subtraction to create the final geometry
    # Add the aggregated white cutouts component to the main component for the boolean operation
    cutouts_ref = c << white_cutouts_aggr
    
    # Perform the subtraction
    final_device_geom = gf.boolean(
        main_rect_ref, 
        cutouts_ref, 
        operation="not", 
        layer=device_layer
    )
    
    # Return a new component containing only the final boolean result
    # (Optional: this cleans up the component of intermediate references)
    c_final = gf.Component("my_final_device")
    c_final << final_device_geom
    return c_final

if __name__ == "__main__":
    device = my_device()
    device.show() # Renders the component to an interactive viewer (if configured)
    device.write_gds("my_device.gds") # Saves the GDSII file