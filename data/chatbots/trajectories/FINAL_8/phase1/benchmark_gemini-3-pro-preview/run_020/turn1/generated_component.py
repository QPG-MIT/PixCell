import gdsfactory as gf

@gf.cell
def tapered_multi_coupler():
    """
    Creates a multi-waveguide coupler consisting of 5 parallel waveguides.
    The outer waveguides are wide and flare out at the ends using S-bends.
    The inner waveguides are narrow and straight.
    
    Fits within a 120um x 4um footprint.
    """
    c = gf.Component()

    # --- Parameters ---
    # Overall dimensions
    length_total = 120.0
    length_straight = 90.0
    length_bend = (length_total - length_straight) / 2
    
    # Cross-section geometry (Y-axis)
    width_wide = 0.85      # Width of the top/bottom outer blocks
    width_narrow = 0.15    # Width of the 3 inner lines
    gap = 0.15             # Gap between waveguides
    
    # Calculate vertical offsets for the parallel section
    # y=0 is the center of the middle narrow waveguide
    y_pitch_narrow = width_narrow + gap
    
    # Inner waveguides y-positions (center lines)
    y_mid = 0
    y_inner_top = y_pitch_narrow
    y_inner_bot = -y_pitch_narrow
    
    # Outer waveguides y-positions (center lines)
    # Distance from center of top inner WG to center of top outer WG:
    # (w_narrow/2) + gap + (w_wide/2)
    offset_wide = (width_narrow / 2) + gap + (width_wide / 2)
    y_outer_top = y_inner_top + offset_wide
    y_outer_bot = -y_outer_top

    # Calculate bend offset (dy) to fit within 4um height
    # Current top edge = y_outer_top + width_wide/2 = ~1.375 um
    # Max top edge allowed = 2.0 um
    # Allowed expansion = ~0.6 um. Let's use 0.5 um for safety.
    dy_bend = 0.5

    # --- Cross Sections ---
    xs_wide = gf.cross_section.cross_section(width=width_wide, layer=(1, 0))
    xs_narrow = gf.cross_section.cross_section(width=width_narrow, layer=(1, 0))

    # --- 1. Inner Waveguides (Straight) ---
    # Create the straight component once and reuse it
    wg_inner = gf.components.straight(length=length_straight, cross_section=xs_narrow)
    
    # Place middle line
    ref_mid = c << wg_inner
    ref_mid.center = (0, y_mid)
    
    # Place top inner line
    ref_in_top = c << wg_inner
    ref_in_top.center = (0, y_inner_top)
    
    # Place bottom inner line
    ref_in_bot = c << wg_inner
    ref_in_bot.center = (0, y_inner_bot)

    # --- 2. Outer Waveguides (Straight Section) ---
    wg_outer = gf.components.straight(length=length_straight, cross_section=xs_wide)
    
    ref_out_top = c << wg_outer
    ref_out_top.center = (0, y_outer_top)
    
    ref_out_bot = c << wg_outer
    ref_out_bot.center = (0, y_outer_bot)

    # --- 3. Outer Waveguides (Bends) ---
    # We use S-bends to flare the outer waveguides away from the center
    # S-bend geometry: size=(length, height_change)
    sbend = gf.components.bend_s(size=(length_bend, dy_bend), cross_section=xs_wide)

    # -- Top Right Bend (Flare Up) --
    # Connects to the right port of the top straight section
    bend_tr = c << sbend
    bend_tr.connect("o1", ref_out_top.ports["o2"])

    # -- Top Left Bend (Flare Up) --
    # Connects to the left port. We mirror the bend horizontally to attach correctly.
    # Alternatively, connect to o1 and let gdsfactory handle the orientation.
    # Since bend_s goes (0,0)->(L, dy), connecting o1 to a left-facing port 
    # will orient the bend to the left, and dy (positive) will go "right" relative to the port 
    # (which is "down" relative to global). We need to check orientation carefully.
    # It is safer to mirror the bend geometry explicitly for the left side.
    
    # Create a mirrored version for the left side (flares up when moving left)
    # Actually, standard bend_s goes Right/Up.
    # If we attach to port o1 (facing Left), the bend points Left.
    # The 'y' component of the bend is relative to the port frame.
    # Left port faces (-1, 0). 'Up' in port frame is (0, -1) (Global Down).
    # We want Global Up. So we need a negative dy relative to the port?
    # Let's just place it manually using mirror to be safe.
    
    bend_tl = c << sbend
    bend_tl.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis (flip X)
    bend_tl.connect("o1", ref_out_top.ports["o1"])

    # -- Bottom Right Bend (Flare Down) --
    # We need a bend that goes Right/Down.
    bend_br = c << sbend
    bend_br.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis (flip Y)
    bend_br.connect("o1", ref_out_bot.ports["o2"])

    # -- Bottom Left Bend (Flare Down) --
    # We need a bend that goes Left/Down.
    # Take the Top Left (Left/Up) and mirror across X.
    bend_bl = c << sbend
    bend_bl.mirror(p1=(0,0), p2=(0,1)) # Flip X
    bend_bl.mirror(p1=(0,0), p2=(1,0)) # Flip Y
    bend_bl.connect("o1", ref_out_bot.ports["o1"])

    return c

if __name__ == "__main__":
    # Create the device
    device = tapered_multi_coupler()
    
    # Save to GDS
    device.write_gds("tapered_coupler.gds")
    
    # Show the device (if running in an environment with a display)
    device.show()