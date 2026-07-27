import gdsfactory as gf

@gf.cell
def get_solid_body():
    """Builds the solid flared block as an isolated component."""
    c = gf.Component()
    
    # 1. Central body
    c << gf.components.rectangle(size=(100, 2.0), layer=(1, 0), centered=True)
    
    # 2. Flares (using tapers)
    # We create the top and bottom flares
    # Using 'taper' to approximate the flare shape
    top_flare = c << gf.components.taper(length=1.5, width1=100, width2=120, layer=(1, 0))
    top_flare.rotate(90)
    top_flare.movey(1.75) # Position slightly above center
    
    bot_flare = c << gf.components.taper(length=1.5, width1=100, width2=120, layer=(1, 0))
    bot_flare.rotate(-90)
    bot_flare.movey(-1.75) # Position slightly below center
    
    return c

@gf.cell
def get_gaps():
    """Builds the gaps as an isolated component."""
    c = gf.Component()
    
    # Create 4 gaps (which creates 5 lines/bars)
    for i in range(4):
        # Calculate Y position for the gaps
        y_offset = (i - 1.5) * 0.4
        c << gf.components.rectangle(size=(130, 0.2), layer=(1, 0), centered=True).movey(y_offset)
        
    return c

@gf.cell
def create_device():
    """Main function to compose and subtract geometries."""
    c = gf.Component()
    
    # Create the two source components
    solid = get_solid_body()
    gaps = get_gaps()
    
    # Perform Boolean NOT (Solid - Gaps = Final Geometry)
    # This creates a new geometry based on the two input components
    final_geo = gf.boolean(solid, gaps, operation="not", layer=(1, 0))
    
    # Add the result to the main component
    c.add_ref(final_geo)
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = create_device()
    
    # Write the file
    device.write_gds("symmetric_device.gds")
    print("Success! 'symmetric_device.gds' generated.")