import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define main body
    # Footprint constraint is 25um x 10um.
    # We choose a main body size of 20um x 4um to leave room for protrusions.
    main_body = gf.components.rectangle(size=(20, 4), layer=layer)
    
    # 2. Define the protrusion shape (using a taper as a geometric primitive)
    # Length 3um, bottom width 3um, top width 1.5um
    protrusion = gf.components.taper(length=3, width1=3, width2=1.5)
    
    # We will accumulate the geometry into this variable using boolean operations
    combined_geometry = main_body
    
    # 3. Create and place the 4 top protrusions
    # We center the body at (0,0). The top edge is at y=2.
    # We space the 4 protrusions along the top.
    top_positions = [-7.5, -2.5, 2.5, 7.5]
    
    for x_pos in top_positions:
        # Create a temporary container for the pillar to perform the move/rotate
        pillar_comp = gf.Component()
        ref = pillar_comp << protrusion
        ref.rotate(90)
        # Position so the base of the pillar (center of bottom width) aligns with the top edge
        # Height of protrusion is 3, so center is at y = 2 + 1.5 = 3.5
        ref.center = (x_pos, 3.5)
        
        # Boolean union to merge into the main shape
        combined_geometry = gf.boolean(combined_geometry, pillar_comp, operation="or", layer=layer)
        
    # 4. Create and place the 1 bottom protrusion
    pillar_comp_bot = gf.Component()
    ref_bot = pillar_comp_bot << protrusion
    ref_bot.rotate(-90)
    # Position on bottom edge (y = -2 - 1.5 = -3.5)
    ref_bot.center = (0, -3.5)
    
    # Final boolean union
    combined_geometry = gf.boolean(combined_geometry, pillar_comp_bot, operation="or", layer=layer)
    
    # Add final unified geometry to the main component
    c << combined_geometry
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device_instance = device()
    device_instance.write_gds("device.gds")
    device_instance.show()