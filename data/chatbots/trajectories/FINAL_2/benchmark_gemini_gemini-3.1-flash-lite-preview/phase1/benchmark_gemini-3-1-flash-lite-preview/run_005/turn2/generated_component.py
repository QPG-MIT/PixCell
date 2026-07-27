import gdsfactory as gf

@gf.cell
def final_device():
    """
    Creates a device with a central block and tapered pillars 
    aligned to match the provided image.
    """
    c = gf.Component()
    
    # 1. Main body
    # Reducing width to 16um and height to 6um to make it compact
    rect = c << gf.components.rectangle(size=(16, 6), centered=True)
    
    # 2. Taper/Pillar definition
    # Using length 3 and widths that create a visible trapezoid
    taper = gf.components.taper(length=3, width1=3.5, width2=2)
    
    # 3. Add Top Pillars
    # The rect height is 6, so the top edge is at y = 3.
    # The taper length is 3. Center of taper is at y = 3 + (3/2) = 4.5
    # Spacing the pillars at -5.5, -1.8, 1.8, 5.5 to get the right density
    top_x_positions = [-5.5, -1.8, 1.8, 5.5]
    
    for x_pos in top_x_positions:
        top_pillar = c << taper
        top_pillar.rotate(90)
        top_pillar.move((x_pos, 4.5))
        
    # 4. Add Bottom Pillar
    # The bottom edge is at y = -3.
    # The taper center is at y = -3 - (3/2) = -4.5
    bot_pillar = c << taper
    bot_pillar.rotate(-90)
    bot_pillar.move((0, -4.5))
    
    return c

# Generate and save
device = final_device()
device.write_gds("device_optimized.gds")