import gdsfactory as gf

@gf.cell
def device_1x4_splitter():
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # Dimensions derived to fit visual proportions and 25x10um constraint
    # Total Height target: 10.0 um
    rect_width = 15.0
    rect_height = 5.0
    
    # Top Tapers configuration
    # Visual observation: Top tapers are about same height as block, maybe slightly shorter
    top_taper_length = 3.5
    top_taper_width_base = 1.8
    top_taper_width_tip = 0.8
    top_pitch = 3.5  # Spacing between tapers
    
    # Bottom Taper configuration
    # Visual observation: Short and stubby
    bot_taper_length = 1.5
    bot_taper_width_base = 2.0
    bot_taper_width_tip = 1.0

    # 1. Create Main Body
    # Using centered rectangle as per catalog
    body = c << gf.components.rectangle(
        size=(rect_width, rect_height), 
        layer=layer, 
        centered=True
    )

    # 2. Create Top Tapers (Array of 4)
    # Define the primitive taper
    taper_top = gf.components.taper(
        length=top_taper_length,
        width1=top_taper_width_base,
        width2=top_taper_width_tip,
        layer=layer
    )
    
    # Place 4 tapers centered along the top edge
    num_tapers = 4
    for i in range(num_tapers):
        # Calculate x-offset to center the group of 4
        # i goes 0..3. (i - 1.5) gives -1.5, -0.5, 0.5, 1.5
        x_pos = (i - (num_tapers - 1) / 2.0) * top_pitch
        
        ref = c << taper_top
        ref.rotate(90)  # Standard taper points +x, rotate to point +y
        # Move base to the top edge of the rectangle
        ref.move((x_pos, rect_height / 2.0))

    # 3. Create Bottom Taper
    # Define the primitive taper
    taper_bot = gf.components.taper(
        length=bot_taper_length,
        width1=bot_taper_width_base,
        width2=bot_taper_width_tip,
        layer=layer
    )
    
    # Place centered on the bottom edge
    ref_bot = c << taper_bot
    ref_bot.rotate(-90)  # Rotate to point -y
    # Move base to the bottom edge of the rectangle
    ref_bot.move((0, -rect_height / 2.0))

    return c

# Generate and save the device
if __name__ == "__main__":
    device = device_1x4_splitter()
    device.write_gds("device_1x4.gds")
    device.show()