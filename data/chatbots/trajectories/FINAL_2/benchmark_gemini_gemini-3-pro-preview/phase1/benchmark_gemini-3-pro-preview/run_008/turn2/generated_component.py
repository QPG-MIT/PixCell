import gdsfactory as gf

@gf.cell
def device_1x4_splitter():
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # Dimensions derived to match the visual weight of the original image
    # and fit within the 25um x 10um footprint constraint.
    
    # Total Height Budget: 10.0 um
    # Allocation: Bottom Taper (1.5) + Body (4.5) + Top Tapers (4.0) = 10.0
    
    # Main Body Dimensions (Wider and shorter than previous iteration)
    rect_width = 14.0
    rect_height = 4.5
    
    # Top Tapers Configuration
    # Adjusted to be much "chunkier" to match the silhouette
    top_taper_length = 4.0
    top_taper_width_base = 3.0  # Wide base leaves small gaps (Pitch 3.5 - Base 3.0 = 0.5 gap)
    top_taper_width_tip = 1.2   # Substantial tip width, not a sharp point
    top_pitch = 3.5             # Spacing between tapers
    
    # Bottom Taper Configuration
    # Short, stubby input coupler
    bot_taper_length = 1.5
    bot_taper_width_base = 3.0
    bot_taper_width_tip = 1.2

    # 1. Create Main Body
    # Using centered rectangle for easier alignment
    body = c << gf.components.rectangle(
        size=(rect_width, rect_height), 
        layer=layer, 
        centered=True
    )

    # 2. Create Top Tapers (Array of 4)
    taper_top_comp = gf.components.taper(
        length=top_taper_length,
        width1=top_taper_width_base,
        width2=top_taper_width_tip,
        layer=layer
    )
    
    num_tapers = 4
    for i in range(num_tapers):
        # Calculate x-offset to center the group of 4
        # i=0 -> -1.5*pitch, i=1 -> -0.5*pitch, etc.
        x_pos = (i - (num_tapers - 1) / 2.0) * top_pitch
        
        ref = c << taper_top_comp
        ref.rotate(90)  # Standard taper points +x, rotate to point +y
        # Move base to the top edge of the rectangle
        ref.move((x_pos, rect_height / 2.0))

    # 3. Create Bottom Taper
    taper_bot_comp = gf.components.taper(
        length=bot_taper_length,
        width1=bot_taper_width_base,
        width2=bot_taper_width_tip,
        layer=layer
    )
    
    ref_bot = c << taper_bot_comp
    ref_bot.rotate(-90)  # Rotate to point -y (down)
    # Move base to the bottom edge of the rectangle
    ref_bot.move((0, -rect_height / 2.0))

    return c

if __name__ == "__main__":
    device = device_1x4_splitter()
    device.write_gds("device_1x4.gds")
    device.show()