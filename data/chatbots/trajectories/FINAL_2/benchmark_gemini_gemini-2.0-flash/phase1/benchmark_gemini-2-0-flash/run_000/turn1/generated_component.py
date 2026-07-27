import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    # Define dimensions
    rect_width = 25
    rect_height = 10
    taper_width = 2
    taper_height = 2
    stem_width = 1
    stem_height = 2.5  # Adjust as necessary

    # Create main rectangle
    rect = c << gf.components.rectangle(size=(rect_width, rect_height))
    rect.move((-rect_width/2, -rect_height/2))

    # Create bottom stem
    stem = c << gf.components.rectangle(size=(stem_width, stem_height))
    stem.move((-stem_width/2, -rect_height/2 - stem_height))

    # Create tapers (4 of them)
    num_tapers = 4
    taper_spacing = rect_width / (num_tapers + 1)  # Calculate spacing

    for i in range(num_tapers):
        x_pos = -rect_width/2 + (i+1) * taper_spacing  # Calculate x position
        
        taper = c << gf.components.rectangle(size=(stem_width, stem_height))

        taper = c << gf.components.taper(length=taper_height, width1=stem_width, width2=stem_width)
        taper.move((-stem_width/2, rect_height/2 ))
        taper_x_offset = -rect_width/2 + (i + 1) * (rect_width / (num_tapers + 1)) - stem_width/2
        taper.move((taper_x_offset, 0))

        taper2 = c << gf.components.rectangle(size=(stem_width, taper_height))

        taper = c << gf.components.rectangle(size=(taper_width/2 , stem_height))
        taper = c << gf.components.rectangle(size=(taper_height/4 , stem_height))
        taper_x_offset = -rect_width/2 + (i + 1) * (rect_width / (num_tapers + 1)) - stem_width/2
        taper.move((taper_x_offset, 5))
        
        
        
        
        
    # Combine shapes (No boolean operation actually needed!)

    return c

# Create and save
device = my_device()
device.show()
device.write_gds("my_device.gds")