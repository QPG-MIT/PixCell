import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the symmetric bar structure matching the provided footprint.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Global Parameters
    bar_thickness = 0.2
    gap = 0.2
    pitch = bar_thickness + gap
    
    # 1. Create Center Stack (5 bars)
    center_width = 100
    for i in range(5):
        # Calculate Y position to keep it centered vertically
        y_pos = (i - 2) * pitch
        bar = gf.components.rectangle(size=(center_width, bar_thickness), layer=layer, centered=True)
        # Explicitly add reference
        ref = c << bar
        ref.movey(y_pos)
        
    # 2. Create Top/Bottom Wings
    # Each wing has 4 bars with decreasing widths
    wing_widths = [80, 65, 50, 35]
    
    for i, w in enumerate(wing_widths):
        # Offset for top and bottom
        y_offset = (i + 1) * pitch + (2 * pitch)
        
        # Top Wing
        bar_top = gf.components.rectangle(size=(w, bar_thickness), layer=layer, centered=True)
        ref_top = c << bar_top
        ref_top.movey(y_offset)
        
        # Bottom Wing
        bar_bot = gf.components.rectangle(size=(w, bar_thickness), layer=layer, centered=True)
        ref_bot = c << bar_bot
        ref_bot.movey(-y_offset)

    # 3. Create Vertical Connectors (The "Bow" walls)
    # Using simple rectangles rotated 90 degrees to represent the pillars
    # Placing them at the ends of the wing stack (approx 40um from center)
    pillar_height = 4 * pitch
    pillar_width = 0.3
    
    for x_pos in [-40, 40]:
        # Top Pillar
        pillar_top = gf.components.rectangle(size=(pillar_width, pillar_height), layer=layer, centered=True)
        ref_p_top = c << pillar_top
        ref_p_top.movex(x_pos)
        ref_p_top.movey(pitch * 4.5)
        
        # Bottom Pillar
        pillar_bot = gf.components.rectangle(size=(pillar_width, pillar_height), layer=layer, centered=True)
        ref_p_bot = c << pillar_bot
        ref_p_bot.movex(x_pos)
        ref_p_bot.movey(-pitch * 4.5)

    return c

if __name__ == "__main__":
    # Create the component
    c = create_device()
    
    # Write to file
    filename = "device.gds"
    c.write_gds(filename)
    print(f"Successfully generated {filename}")