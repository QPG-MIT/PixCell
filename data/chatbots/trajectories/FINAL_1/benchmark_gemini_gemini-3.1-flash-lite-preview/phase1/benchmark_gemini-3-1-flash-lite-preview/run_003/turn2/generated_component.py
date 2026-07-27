import gdsfactory as gf

@gf.cell
def fork_device():
    """
    Recreates the device by carving gaps out of a solid block.
    This ensures the needle and arms are connected as a single structure.
    """
    c = gf.Component()
    
    # 1. Define the base footprint (The full solid shape)
    base = gf.components.rectangle(size=(40, 1.7), layer=(1, 0), centered=False)
    
    # 2. Define the cutouts (The gaps)
    # We use a taper to create the triangular gaps.
    # Length=28 to leave a solid block on the right.
    # width1=0.05 (near the tip), width2=0.45 (the flare)
    gap_cutter = gf.components.taper(length=28, width1=0.05, width2=0.45, layer=(1, 0))
    
    # 3. Position the cutouts
    # We need to subtract the gap twice: once for the top gap, once for the bottom.
    # The 'base' has a height of 1.7. 
    # Center y = 0.85. 
    # We shift the cutouts up and down to define the needle width and arm thickness.
    
    # Create top cutout
    top_gap = gf.Component()
    top_gap_ref = top_gap << gap_cutter
    top_gap_ref.movey(1.15) # Shifted up
    
    # Create bottom cutout
    bot_gap = gf.Component()
    bot_gap_ref = bot_gap << gap_cutter
    bot_gap_ref.movey(0.55) # Shifted down
    
    # 4. Perform Boolean Subtraction
    # First, subtract the top gap from the base
    step1 = gf.boolean(base, top_gap, operation="not", layer=(1, 0))
    
    # Then, subtract the bottom gap from the result
    final_geometry = gf.boolean(step1, bot_gap, operation="not", layer=(1, 0))
    
    # Add the final result to our component
    c << final_geometry
    
    return c

# Generate and save
device = fork_device()
device.write_gds("fork_device.gds")