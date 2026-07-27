import gdsfactory as gf

@gf.cell
def tapered_coupler_array():
    """
    Creates a dense waveguide mode-converter/coupler array.
    Central bus of 5 straight waveguides.
    Flanked by 2 straight waveguides and a large outer adiabatic taper block.
    """
    c = gf.Component()
    
    # =========================================================================
    # Parameters
    # =========================================================================
    L = 120.0       # Length of the device
    w = 0.2         # Waveguide width
    g = 0.1         # Gap between waveguides (slightly larger for visibility)
    pitch = w + g
    
    # Layer definition
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=w, layer=layer)

    # =========================================================================
    # 1. Central Bus (5 straight waveguides)
    # =========================================================================
    # Centered at y=0. Indices -2, -1, 0, 1, 2
    for i in range(-2, 3):
        wg = c << gf.components.straight(length=L, cross_section=xs)
        wg.y = i * pitch
        wg.x = 0 # Centered at x=0
        
    # Calculate the Y-coordinate of the top edge of this central group
    # Top center is at 2*pitch. Top edge is at 2*pitch + w/2.
    y_center_top_edge = 2 * pitch + w / 2

    # =========================================================================
    # 2. Top Flank Structure
    # =========================================================================
    
    # A. Two Straight Flank Lines
    y_flank_start = y_center_top_edge + g
    for i in range(2):
        y_pos = y_flank_start + w/2 + i * pitch
        wg = c << gf.components.straight(length=L, cross_section=xs)
        wg.y = y_pos
        wg.x = 0

    # Calculate top edge of the flank lines
    # Center of 2nd line is at index 1: y_flank_start + w/2 + pitch
    # Top edge is center + w/2 = y_flank_start + w + pitch
    y_flank_top_edge = y_flank_start + 2*w + g

    # B. Asymmetric Taper Block ("Butterfly" shape)
    # This block fills the remaining space up to y=2.0um (half of 4.0um footprint)
    y_taper_bottom = y_flank_top_edge + g
    y_max_limit = 2.0
    
    h_taper_max = y_max_limit - y_taper_bottom  # Height at the ends (thickest)
    h_taper_min = w                             # Height at the waist (thinnest)
    
    # --- Construct the Taper Geometry via Boolean Operations ---
    # We start with a full rectangle and cut away the top part to create the curve.
    # The curve needs to be high at ends and low in center -> U-shaped cut.
    
    # Base Rectangle centered at (0,0) locally
    rect = gf.components.rectangle(size=(L, h_taper_max), layer=layer, centered=True)
    
    # Create the "Cutter" mask (The negative space)
    # The cutter must be a shape that goes down in the first half and up in the second half.
    # We use S-bends to create a smooth adiabatic profile.
    cutter = gf.Component()
    cutter_w = 20.0 # Large width to ensure we clear all material above the curve
    drop = h_taper_max - h_taper_min
    
    # Left Half: Curve down
    # S-bend from (-L/2, Top) to (0, Waist)
    sb_down = gf.components.bend_s(
        size=(L/2, -drop), 
        cross_section=gf.cross_section.cross_section(width=cutter_w)
    )
    ref_down = cutter << sb_down
    # Position: Start at x=-L/2.
    # We want the BOTTOM edge of the cutter to be at the TOP of the rect (h_taper_max/2).
    # bend_s starts at (0,0). Center at (0,0). Bottom edge at -cutter_w/2.
    # Shift to align bottom edge: y_shift = h_taper_max/2 + cutter_w/2.
    ref_down.move((-L/2, h_taper_max/2 + cutter_w/2))
    
    # Right Half: Curve up
    # S-bend from (0, Waist) to (L/2, Top)
    sb_up = gf.components.bend_s(
        size=(L/2, drop), 
        cross_section=gf.cross_section.cross_section(width=cutter_w)
    )
    ref_up = cutter << sb_up
    # Position: Start at x=0.
    # We want the BOTTOM edge of the cutter to be at the Waist height.
    # Waist height relative to rect center: Top_of_rect - drop.
    # y_target = h_taper_max/2 - drop.
    # Shift to align bottom edge: y_shift = y_target + cutter_w/2.
    ref_up.move((0, (h_taper_max/2 - drop) + cutter_w/2))
    
    # Perform Boolean Subtract
    asym_taper = gf.boolean(rect, cutter, operation="not", layer=layer)
    
    # --- Place Top Taper ---
    t_top = c << asym_taper
    # Align bottom of taper to y_taper_bottom
    # asym_taper local bottom is -h_taper_max/2
    t_top.move((0, y_taper_bottom + h_taper_max/2))

    # =========================================================================
    # 3. Bottom Flank Structure (Mirror)
    # =========================================================================
    
    # Mirror Flank Lines
    for i in range(2):
        y_pos = y_flank_start + w/2 + i * pitch
        wg = c << gf.components.straight(length=L, cross_section=xs)
        wg.y = -y_pos
        wg.x = 0
        
    # Mirror Taper Block
    t_bot = c << asym_taper
    t_bot.mirror() # Flips y -> -y.
    # After mirror:
    # Flat edge (was bottom) is now Top at y = -(-h_taper_max/2) = h_taper_max/2? 
    # No, mirror maps y to -y.
    # Original bottom y = -h_taper_max/2 maps to h_taper_max/2 (new top).
    # Original top y = h_taper_max/2 maps to -h_taper_max/2 (new bottom).
    # We want the new Flat Top to be at -y_taper_bottom.
    # Current Flat Top is at h_taper_max/2.
    # Move y by: -y_taper_bottom - h_taper_max/2.
    t_bot.move((0, -y_taper_bottom - h_taper_max/2))

    return c

# Generate and visualize
device = tapered_coupler_array()
device.write_gds("tapered_coupler_array.gds")
device.show()