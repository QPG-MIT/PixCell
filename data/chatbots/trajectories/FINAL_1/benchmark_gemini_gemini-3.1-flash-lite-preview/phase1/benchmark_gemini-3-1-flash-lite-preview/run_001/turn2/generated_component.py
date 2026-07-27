import gdsfactory as gf

@gf.cell
def final_device():
    c = gf.Component()
    
    # 1. Define a standard strip cross-section
    # Using 1nm grid settings implicitly via components
    xs = gf.cross_section.strip(width=0.5, layer=(1, 0))
    
    # 2. Central Taper (The "wedge")
    # Using integers to ensure grid alignment
    center_taper = c << gf.components.taper(
        length=40, 
        width1=0.2, 
        width2=1.0, 
        cross_section=xs
    )
    
    # 3. Outer Arms
    # We use bend_s with clean, grid-aligned dimensions
    # size=(length, vertical_displacement)
    # Using integers (20, 2) guarantees no floating-point artifacts
    bend_params = dict(size=(20, 2), cross_section=xs)
    
    top_arm = c << gf.components.bend_s(**bend_params)
    bot_arm = c << gf.components.bend_s(**bend_params)
    
    # 4. Positioning
    # Explicitly move to fixed coordinates to prevent sub-grid creep
    top_arm.movey(2)
    bot_arm.movey(-2)
    
    # 5. Fix Grid Errors
    # The 'flatten' operation snaps all coordinates to the foundry 
    # defined grid, preventing the "off-grid instances" error.
    c.flatten()
    
    return c

# Create and export
device = final_device()
device.write_gds("device_grid_fixed.gds")
device.show()