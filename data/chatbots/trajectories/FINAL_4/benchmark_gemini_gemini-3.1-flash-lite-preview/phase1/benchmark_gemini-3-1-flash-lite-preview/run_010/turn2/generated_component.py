import gdsfactory as gf

@gf.cell
def custom_directional_coupler():
    c = gf.Component()
    
    # 1. Define the cross-section
    # 0.5um width is standard and fits well within the 3um height
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Parameters
    length = 18
    # Shift vertical position by 0.5um to make them approach each other
    offset = 0.5 

    # 3. Create S-bends
    # Top waveguide curves down
    top_wg = c << gf.components.bend_s(size=(length, -offset), cross_section=xs)
    # Bottom waveguide curves up
    bot_wg = c << gf.components.bend_s(size=(length, offset), cross_section=xs)
    
    # 4. Positioning
    # Align the waveguides so they are centered in the 3um vertical space
    top_wg.movey(0.75)
    bot_wg.movey(-0.75)
    
    # 5. Fix grid snapping errors
    # Flattening combines the instances into one geometry,
    # ensuring all coordinates are snapped to the manufacturing grid.
    c.flatten()

    return c

# Generate the component
device = custom_directional_coupler()

# Display or save the device
device.show()
device.write_gds("coupler.gds")