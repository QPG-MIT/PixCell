import gdsfactory as gf

@gf.cell
def custom_device_assembly():
    """
    Creates a device composed of a central rectangular block,
    4 top pillars, and 1 bottom pillar.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define the main rectangular body
    # Size: (25um, 4um) to fit into the 10um height constraint
    main_body = c << gf.components.rectangle(size=(25, 4), layer=layer, centered=True)
    
    # 2. Add Top Pillars
    # We want 4 pillars. Spaced at x = -9, -3, 3, 9
    # Pillar size: 2um wide, 3um tall.
    # The main body is centered at (0,0), with top edge at y=2.
    # To sit on the edge, the center of these pillars must be at y=3.5 (2 + 1.5)
    for x_pos in [-9, -3, 3, 9]:
        pillar = c << gf.components.rectangle(size=(2, 3), layer=layer, centered=True)
        pillar.move((x_pos, 3.5))
        
    # 3. Add Bottom Pillar
    # Size: 2um wide, 3um tall.
    # Main body bottom edge is at y=-2.
    # To sit on the bottom edge, the center of this pillar must be at y=-3.5 (-2 - 1.5)
    bottom_pillar = c << gf.components.rectangle(size=(2, 3), layer=layer, centered=True)
    bottom_pillar.move((0, -3.5))
    
    return c

# Create and save the device
if __name__ == "__main__":
    device = custom_device_assembly()
    device.write_gds("custom_device.gds")
    
    # Optional: Display the device
    # device.show()