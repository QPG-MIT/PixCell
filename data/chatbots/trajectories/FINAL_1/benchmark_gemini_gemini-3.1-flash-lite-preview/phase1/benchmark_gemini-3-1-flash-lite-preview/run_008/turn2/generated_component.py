import gdsfactory as gf

@gf.cell
def three_parallel_tapers():
    """
    Recreates the geometry from the image: 
    Three parallel tapering waveguide sections.
    """
    c = gf.Component()
    
    # Parameters based on the 40um footprint
    length = 40.0
    
    # Define three different taper widths to create the "spike" and arm effect
    # Top and Bottom arms: Start wide, end narrow
    # Middle arm: Starts narrow, ends wide (the "spike")
    top_taper = gf.components.taper(length=length, width1=0.6, width2=0.3)
    bot_taper = gf.components.taper(length=length, width1=0.6, width2=0.3)
    mid_taper = gf.components.taper(length=length, width1=0.2, width2=0.4)
    
    # Add to component
    top = c << top_taper
    bot = c << bot_taper
    mid = c << mid_taper
    
    # Position them in parallel along the Y-axis
    # Spacing them out to fit the ~1.7um total height constraint
    top.movey(0.6)
    bot.movey(-0.6)
    # mid remains at y=0
    
    # Flatten to resolve off-grid instance errors
    c.flatten()
    
    return c

# Generate and save
device = three_parallel_tapers()
device.write_gds("tapered_structure.gds")

# Preview
device.show()