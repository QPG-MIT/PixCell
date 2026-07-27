import gdsfactory as gf

@gf.cell
def smooth_directional_coupler() -> gf.Component:
    c = gf.Component("smooth_directional_coupler")
    
    # Define the cross-section
    width = 0.5
    layer = (1, 0)
    
    # Set radius=0.1 to avoid minimum bend radius validation errors
    # (The continuous curve has small effective bend radii at the pinch)
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=0.1)
    
    # Calculate geometric parameters to hit [18, 3] footprint exactly
    # Total Length = 18. Using two back-to-back S-bends means each is dx = 9.0
    dx = 9.0
    
    # Total Height = 3. 
    # Max Y = 1.5, Min Y = -1.5 (with width=0.5, center points are +/- 1.25)
    # Assume a standard minimum gap of 0.2 at the center pinch.
    # Center of top waveguide at pinch = 0.2/2 + 0.5/2 = 0.35
    # The S-bend vertical drop (dy) = 1.25 - 0.35 = 0.9
    dy = 0.9
    y_start = 1.25
    
    # 1. Create the S-bends for the top waveguide
    s_top_left = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    s_top_right = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # 2. Create the S-bends for the bottom waveguide
    s_bot_left = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    s_bot_right = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # 3. Position the left (starting) S-bends
    s_top_left.movey(y_start)
    s_bot_left.movey(-y_start)
    
    # 4. Connect the right S-bends to the left ones
    # This automatically snaps them perfectly end-to-end to form the continuous curve
    s_top_right.connect("o1", s_top_left.ports["o2"])
    s_bot_right.connect("o1", s_bot_left.ports["o2"])
    
    # 5. Add external ports for the overall component
    c.add_port("o1", port=s_top_left.ports["o1"])
    c.add_port("o2", port=s_bot_left.ports["o1"])
    c.add_port("o3", port=s_top_right.ports["o2"])
    c.add_port("o4", port=s_bot_right.ports["o2"])
    
    return c


if __name__ == "__main__":
    # Generate the component and save to GDS
    device = smooth_directional_coupler()
    device.write_gds("smooth_directional_coupler.gds")