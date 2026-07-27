import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Directional coupler with a 120um x 4um footprint.
    Refined parameters to match the visual proportions of the reference image:
    - Thicker waveguides (0.8um)
    - Shorter straight coupling section (30um)
    - Longer S-bends for smoother curvature (45um each)
    """
    c = gf.Component()

    # --- Constraints ---
    total_length = 120.0
    total_height = 4.0

    # --- Geometric Parameters ---
    # Width increased to 0.8um to match the line weight in the image relative to height.
    wg_width = 0.8
    # Gap kept tight at 0.2um.
    coupling_gap = 0.2
    
    # Longitudinal dimensions adjusted:
    # Straight section reduced to 30um (1/4 of total) to allow for longer, smoother bends.
    length_straight = 30.0 
    length_bend = (total_length - length_straight) / 2  # Result: 45.0 um per bend

    # --- Y-Axis Calculations ---
    # Define vertical positions to fit exactly within 4.0um height.
    # Outer ports (centered vertically within the top/bottom bounds)
    # Top Y = +2.0 - (Width/2)
    y_io_top = (total_height / 2) - (wg_width / 2)
    
    # Inner coupling region
    # Top Y = + (Gap/2) + (Width/2)
    y_couple_top = (coupling_gap / 2) + (wg_width / 2)
    
    # Calculate the vertical shift (dy) required for the S-bends
    dy = y_io_top - y_couple_top

    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Geometry Construction ---

    # 1. Central Straight Section
    # Placed in the middle of the device longitudinally
    wg_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    
    # Move straights to their specific coupling positions
    wg_top.move((length_bend, y_couple_top))
    wg_bot.move((length_bend, -y_couple_top))

    # 2. Input S-Bends (Left Side)
    # Top Input: Transitions from high (IO) to low (Coupling)
    # We construct a bend of size (L, -dy) and place it at the IO start height.
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_in_top.move((0, y_io_top))
    
    # Bottom Input: Transitions from low (IO) to high (Coupling)
    # We construct a bend of size (L, dy) and place it at the IO start height.
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.move((0, -y_io_top))

    # 3. Output S-Bends (Right Side)
    # Top Output: Transitions from low (Coupling) to high (IO)
    # Connects to the end of the top straight section.
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_top.ports["o2"])
    
    # Bottom Output: Transitions from high (Coupling) to low (IO)
    # Connects to the end of the bottom straight section.
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=bend_in_bot.ports["o1"]) # Bottom Left
    c.add_port("o2", port=bend_in_top.ports["o1"]) # Top Left
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Right
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Right

    return c

# Generate and save
device = directional_coupler_refined()
device.write_gds("directional_coupler_refined.gds")