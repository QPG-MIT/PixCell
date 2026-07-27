import gdsfactory as gf
import numpy as np

@gf.cell
def my_device():
    c = gf.Component()
    
    # Define parameters based on footprint and image analysis
    total_width = 120.0
    total_height = 4.0
    
    # Line width and gap width derived from total height and number of features
    # (5 black lines + 4 white gaps = 9 features)
    line_width = total_height / 9 
    gap_width = total_height / 9
    
    # 1. Create the main solid black rectangle
    main_rect = c << gf.components.rectangle(
        size=(total_width, total_height), 
        layer=(1, 0), 
        centered=True
    )
    
    # 2. Define cross-section for the white channels (used for extrusion)
    cutout_xs = gf.cross_section.cross_section(width=gap_width, layer=(1, 0))
    
    # 3. Define channel geometry parameters
    R_bend_channel = 10  # Radius for the Euler bends
    
    # The straight part of the channel's centerline.
    # Total width (120) = horizontal span of left bend (R_bend) + straight length + horizontal span of right bend (R_bend)
    L_straight_channel_mid = total_width - 2 * R_bend_channel # = 120 - 20 = 100 um
    
    # Y-centers for the 4 white channels (derived in the thought process)
    # [4/3, 4/9, -4/9, -4/3] um
    channel_y_centers = [
        (2 * line_width + 2 * gap_width + line_width/2 + gap_width/2) - total_height/2, # Top-most gap
        (line_width + gap_width + line_width/2 + gap_width/2) - total_height/2,         # Second gap
        -(line_width + gap_width + line_width/2 + gap_width/2) + total_height/2,        # Third gap
        -(2 * line_width + 2 * gap_width + line_width/2 + gap_width/2) + total_height/2 # Bottom-most gap
    ]
    # Simplified calculation:
    channel_y_centers = [4/3, 4/9, -4/9, -4/3]
    
    # Store the channel components before boolean operations
    channel_components = []

    # 4. Create and position each channel
    for y_center in channel_y_centers:
        p = gf.Path()
        
        # Path for one channel. The shape is straight-bend-straight-bend-straight.
        # The Euler bend in GDSFactory contributes 'radius' to its X and Y span.
        # This path creates a shape that is straight in the middle, and then curves
        # outwards at both ends.
        
        # Short initial horizontal segment (aligns the bend's entry point)
        p.append(gf.path.straight(length=R_bend_channel)) 

        if y_center > 0: # Channels above the centerline (y=0)
            # Left bend: curves from horizontal (direction 0) up to vertical (direction 90)
            p.append(gf.path.euler(radius=R_bend_channel, angle=90, p=0.5)) 
            # Central straight horizontal segment
            p.append(gf.path.straight(length=L_straight_channel_mid - 2 * R_bend_channel)) # Adjust length if bends overlap in X
            # Right bend: curves from vertical (direction 90) down to horizontal (direction 0)
            p.append(gf.path.euler(radius=R_bend_channel, angle=-90, p=0.5)) 
        else: # Channels below the centerline (y=0)
            # Left bend: curves from horizontal (direction 0) down to vertical (direction -90 or 270)
            p.append(gf.path.euler(radius=R_bend_channel, angle=-90, p=0.5)) 
            # Central straight horizontal segment
            p.append(gf.path.straight(length=L_straight_channel_mid - 2 * R_bend_channel)) # Adjust length if bends overlap in X
            # Right bend: curves from vertical (direction -90) up to horizontal (direction 0)
            p.append(gf.path.euler(radius=R_bend_channel, angle=90, p=0.5)) 
            
        # Short final horizontal segment (aligns the bend's exit point)
        p.append(gf.path.straight(length=R_bend_channel)) 

        # Extrude the path to create the channel geometry
        channel_ref = c << gf.path.extrude(p, cross_section=cutout_xs)
        
        # Position the channel. The path's start is at (0,0), so it needs to be moved.
        # The path starts at x=0, so to center it at x=0 for total_width 120:
        # The center of the path is at x = (R_bend_channel + R_bend_channel + L_straight_channel_mid - 2*R_bend_channel + R_bend_channel) / 2
        # This simplifies to x = L_straight_channel_mid / 2 + R_bend_channel
        # A simple move to the center of the total device width: (-total_width/2 + path_total_length/2)
        
        # Let's compute the total path length (which affects its final x-position after extrude)
        # For a path sequence straight(L1) - euler(R, 90) - straight(L2) - euler(R, -90) - straight(L3)
        # The total length along the path is L1 + R*pi/2 + L2 + R*pi/2 + L3
        # However, `extrude` positions based on the `Path`'s points.
        
        # The path is defined to conceptually span `total_width`, starting at 0.
        # Moving it by `-total_width / 2` should center it.
        channel_ref.movex(-total_width / 2)
        channel_ref.movey(y_center)
        
        channel_components.append(channel_ref)

    # 5. Perform boolean subtraction to create the final geometry
    # Iteratively subtract each channel
    final_device = main_rect
    for channel_ref in channel_components:
        final_device = gf.boolean(final_device, channel_ref, operation="not", layer=(1,0))
    
    # Replace the initial main_rect with the final boolean result
    # We create a new component for the final result to have clean ports if needed,
    # or just return the final boolean operation's component.
    c_final = gf.Component()
    c_final << final_device
    return c_final

if __name__ == "__main__":
    device = my_device()
    device.show() # Renders the component to an interactive viewer (if configured)
    device.write_gds("my_device.gds") # Saves the GDSII file