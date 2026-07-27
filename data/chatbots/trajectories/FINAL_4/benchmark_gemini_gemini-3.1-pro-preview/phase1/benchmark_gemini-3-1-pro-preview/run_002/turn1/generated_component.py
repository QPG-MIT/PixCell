import gdsfactory as gf

@gf.cell
def coupler_sbends(
    length: float = 18.0, 
    height: float = 3.0, 
    wg_width: float = 0.5, 
    gap: float = 0.2
) -> gf.Component:
    """
    Creates a symmetrical coupler-like structure using back-to-back S-bends.
    Matches the footprint of [18, 3].
    """
    c = gf.Component("coupler_sbends")
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Calculate geometric parameters
    # The total length is 18, so each S-bend is half of that
    half_length = length / 2.0
    
    # Center-to-center distance at the outer edges
    # Outer bound to outer bound is 'height' (3.0). 
    # Center to center = height - wg_width = 3.0 - 0.5 = 2.5
    # Waveguides start/end at y = ±1.25
    y_end = (height - wg_width) / 2.0
    
    # Center-to-center distance at the middle (closest point)
    # Mid center to center = gap + wg_width = 0.2 + 0.5 = 0.7
    # Waveguides dip to y = ±0.35
    y_mid = (gap + wg_width) / 2.0
    
    # Calculate the vertical shift for the first S-bends
    dy = y_mid - y_end  # Will be -0.9 for the top arm
    
    # --- Top Arm ---
    # First half goes inward
    top_left = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    # Second half goes outward (opposite dy)
    top_right = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    
    # --- Bottom Arm ---
    # First half goes inward (opposite dy of top arm)
    bot_left = c << gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    # Second half goes outward
    bot_right = c << gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    
    # --- Positioning and Connections ---
    # Move starting ports to their respective y-coordinates
    top_left.move((0, y_end))
    bot_left.move((0, -y_end))
    
    # Connect the second halves to the first halves
    top_right.connect("o1", top_left.ports["o2"])
    bot_right.connect("o1", bot_left.ports["o2"])
    
    # Add ports to the final component
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Build the device
    c = coupler_sbends()
    # Save to a GDS file (fixes the 'No GDS file produced' error)
    c.write_gds("coupler_sbends.gds")