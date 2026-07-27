import gdsfactory as gf

@gf.cell
def create_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Parameters
    bar_height = 0.2
    gap = 0.4
    pitch = bar_height + gap
    center_width = 100.0
    
    # 1. Create Center Stack (5 bars)
    for i in range(5):
        y_pos = (i - 2) * pitch
        bar = gf.components.rectangle(size=(center_width, bar_height), layer=layer, centered=True)
        ref = c << bar
        ref.movey(round(y_pos, 3))
        
    # 2. Create Top/Bottom Wings
    # Each wing has 4 bars with decreasing widths
    wing_widths = [80.0, 65.0, 50.0, 35.0]
    
    for side in [1, -1]: # 1 for top, -1 for bottom
        # Offset for the wing section
        y_offset_start = 2.5 * pitch * side
        
        for i, w in enumerate(wing_widths):
            # Calculate Y position
            y_pos = y_offset_start + ((i + 0.5) * pitch * side)
            
            bar = gf.components.rectangle(size=(w, bar_height), layer=layer, centered=True)
            ref = c << bar
            ref.movey(round(y_pos, 3))
            
        # 3. Create Vertical Rails (Straight, no rotation needed)
        # Place rails at the edges of the widest wing bar
        rail_height = 4 * pitch
        rail_width = 0.4
        rail_x = (wing_widths[0] / 2)
        rail_y = y_offset_start + (2 * pitch * side)
        
        for x_sign in [-1, 1]:
            rail = gf.components.rectangle(size=(rail_width, rail_height), layer=layer, centered=True)
            ref_rail = c << rail
            ref_rail.movex(round(x_sign * rail_x, 3))
            ref_rail.movey(round(rail_y, 3))

    # flatten() merges all references, which resolves grid issues and is standard for finalized cells
    c.flatten()
    return c

if __name__ == "__main__":
    # Create the component
    c = create_device()
    
    # Write to file
    filename = "device.gds"
    c.write_gds(filename)
    print(f"Successfully generated {filename}")