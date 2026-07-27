import gdsfactory as gf

@gf.cell
def fan_out_device():
    """
    Creates a symmetric fan-out structure:
    - A central vertical stack of rectangular blocks.
    - Curved Euler bends extending from the edges of these blocks.
    """
    c = gf.Component()
    
    # Parameters
    num_waveguides = 5
    pitch = 4.0             # Vertical distance between centers
    central_block_width = 40.0
    central_block_height = 2.0
    
    # 1. Create the central rectangular spine
    # We loop to create 5 distinct rectangles to match the target visual
    for i in range(-(num_waveguides // 2), (num_waveguides // 2) + 1):
        y_pos = i * pitch
        
        # Add the central rectangle
        rect = c << gf.components.rectangle(
            size=(central_block_width, central_block_height), 
            layer=(1, 0),
            centered=True
        )
        rect.movey(y_pos)
        
        # 2. Add Top and Bottom Bends
        # We attach bends to the sides of the central block
        # Top Bend
        bend_top = c << gf.components.bend_euler(
            radius=15, 
            angle=45, 
            layer=(1, 0)
        )
        # Position the bend at the right edge of the rectangle
        # Bend 'o1' connects to the rectangle's general area
        bend_top.move((central_block_width / 2, y_pos + central_block_height / 2))
        
        # Bottom Bend (Mirrored)
        bend_bottom = c << gf.components.bend_euler(
            radius=15, 
            angle=-45, 
            layer=(1, 0)
        )
        # Position the bend at the right edge
        bend_bottom.move((central_block_width / 2, y_pos - central_block_height / 2))
        
        # Optional: Add symmetrical left-side bends to complete the "bow-tie" look
        bend_top_left = c << gf.components.bend_euler(
            radius=15, 
            angle=135, 
            layer=(1, 0)
        )
        bend_top_left.move((-central_block_width / 2, y_pos + central_block_height / 2))
        
        bend_bottom_left = c << gf.components.bend_euler(
            radius=15, 
            angle=-135, 
            layer=(1, 0)
        )
        bend_bottom_left.move((-central_block_width / 2, y_pos - central_block_height / 2))

    return c

# Generate and save
device = fan_out_device()
device.write_gds("fan_out_device_v2.gds")