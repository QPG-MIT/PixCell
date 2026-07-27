import gdsfactory as gf

@gf.cell
def striped_coupler_explicit():
    """
    Recreates the asymmetric striped directional coupler using explicit waveguide routing.
    This avoids extrusion artifacts by treating each stripe as an independent trace.
    
    Structure:
    - 2 Arms (Top and Bottom)
    - Each Arm: 3 Thin Inner Lines + 1 Thick Outer Block
    - Geometry: S-bend Input -> Straight Coupling -> S-bend Output
    """
    c = gf.Component()

    # --- Dimensions & Parameters ---
    # Longitudinal (Length)
    len_bend = 30.0
    len_straight = 60.0
    
    # Transverse (Widths & Gaps)
    w_thin = 0.1        # Width of the 3 inner lines
    w_thick = 0.6       # Width of the 1 outer block
    gap_lines = 0.1     # Gap between lines within an arm
    gap_couple = 0.2    # Gap between Top and Bottom arms in the center
    
    # Vertical Flare (Input/Output offset)
    # The arms are closer in the center and flare out at the ends.
    dy_flare = 0.7 

    # --- Geometry Calculation ---
    
    # We calculate the Y-center position for each of the 4 lines in the Top Arm
    # relative to the device center (y=0).
    # We build outwards: Inner Line 1 -> Line 2 -> Line 3 -> Thick Line 4
    
    # Line 1 (Innermost)
    y1 = (gap_couple / 2) + (w_thin / 2)
    
    # Line 2
    y2 = y1 + (w_thin / 2) + gap_lines + (w_thin / 2)
    
    # Line 3
    y3 = y2 + (w_thin / 2) + gap_lines + (w_thin / 2)
    
    # Line 4 (Outermost, Thick)
    y4 = y3 + (w_thin / 2) + gap_lines + (w_thick / 2)

    # Bundle the configuration
    y_offsets = [y1, y2, y3, y4]
    widths = [w_thin, w_thin, w_thin, w_thick]

    # --- Helper Function ---
    def add_trace(component, y_center_straight, width, dy, is_top=True):
        """
        Generates a single waveguide trace: Input Bend -> Straight -> Output Bend.
        """
        # Define cross-section for this specific line
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
        
        # 1. Straight Section (Central Coupling Region)
        straight = component << gf.components.straight(
            length=len_straight, 
            cross_section=xs
        )
        straight.movey(y_center_straight)
        
        # 2. Input S-Bend
        # Top Arm: Starts High, goes DOWN (-dy) to meet straight.
        # Bot Arm: Starts Low, goes UP (+dy) to meet straight.
        bend_height = -dy if is_top else dy
        
        bend_in = component << gf.components.bend_s(
            size=(len_bend, bend_height), 
            cross_section=xs
        )
        # Connect: Bend Output (o2) -> Straight Input (o1)
        bend_in.connect("o2", straight.ports["o1"])
        
        # 3. Output S-Bend
        # Top Arm: Starts at straight, goes UP (+dy).
        # Bot Arm: Starts at straight, goes DOWN (-dy).
        bend_out_height = dy if is_top else -dy
        
        bend_out = component << gf.components.bend_s(
            size=(len_bend, bend_out_height), 
            cross_section=xs
        )
        # Connect: Straight Output (o2) -> Bend Input (o1)
        bend_out.connect("o1", straight.ports["o2"])

    # --- Assembly ---
    
    # Generate Top Arm Lines
    for y, w in zip(y_offsets, widths):
        add_trace(c, y_center_straight=y, width=w, dy=dy_flare, is_top=True)

    # Generate Bottom Arm Lines (Mirrored Y positions)
    for y, w in zip(y_offsets, widths):
        add_trace(c, y_center_straight=-y, width=w, dy=dy_flare, is_top=False)

    return c

# Create and save
device = striped_coupler_explicit()
device.show()
device.write_gds("striped_coupler_final.gds")