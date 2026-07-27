import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Main body (Rectangle)
    # Using 18x4 to stay within the 25x10 footprint constraints
    main_body = gf.components.rectangle(size=(18, 4), layer=layer)
    
    # 2. Define the protrusion shape
    # Taper length 3, width 2.5 to 1
    taper_comp = gf.components.taper(length=3, width1=2.5, width2=1.0)
    
    # We will accumulate the geometry here
    combined_geometry = main_body
    
    # Overlap amount to ensure clean boolean union
    overlap = 0.5
    
    # 3. Create top protrusions
    # Top edge of rectangle is at y = 2. 
    # To overlap by 0.5, the base of the pillar should be at y = 1.5.
    # The taper is 3um long, so its center is 1.5 + 1.5 = 3.0.
    top_positions = [-6, -2, 2, 6]
    for x_pos in top_positions:
        # Create a container for the individual pillar to perform placement
        pillar_container = gf.Component()
        ref = pillar_container << taper_comp
        ref.rotate(90)
        ref.center = (x_pos, 3.0)
        
        # Boolean union
        combined_geometry = gf.boolean(combined_geometry, pillar_container, operation="or", layer=layer)
        
    # 4. Create bottom protrusion
    # Bottom edge of rectangle is at y = -2.
    # To overlap by 0.5, the base of the pillar should be at y = -1.5.
    # The center of the taper is -1.5 - 1.5 = -3.0.
    pillar_container_bot = gf.Component()
    ref_bot = pillar_container_bot << taper_comp
    ref_bot.rotate(-90)
    ref_bot.center = (0, -3.0)
    
    # Final Boolean union
    combined_geometry = gf.boolean(combined_geometry, pillar_container_bot, operation="or", layer=layer)
    
    c << combined_geometry
    return c

# Generate and save
if __name__ == "__main__":
    device_instance = device()
    device_instance.write_gds("device.gds")
    device_instance.show()