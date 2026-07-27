import gdsfactory as gf

@gf.cell
def device_inverse_taper_coupler():
    """
    Creates an inverse taper coupler geometry matched to the reference image.
    
    Structure:
    - Central waveguide: Linearly tapers from a wide input to a sharp tip.
    - Outer waveguides: Start parallel with a tight gap, then flare outwards via S-bends.
    
    Footprint Constraint: 40.0 um x 1.7 um
    """
    c = gf.Component()

    # --- Parameters ---
    # Global dimensions
    length = 40.0
    footprint_height = 1.7
    
    # Waveguide Geometry (Visual estimation)
    w_center = 0.60        # Width of central waveguide at input
    w_side = 0.30          # Width of outer waveguides
    w_tip = 0.05           # Tip width of the central taper
    gap_in = 0.10          # Initial gap between center and sides (very tight)
    
    # Longitudinal Layout
    l_straight = 12.0      # Length of the parallel straight section
    l_bend = length - l_straight # Remaining length for the S-bend flare
    l_taper = 32.0         # Taper length (ends before the output edge)

    # Vertical Calculation
    # Input Y-offsets (tightly packed)
    # Center is at y=0. Side center is at (w_center/2 + gap + w_side/2)
    y_in_offset = (w_center / 2) + gap_in + (w_side / 2)
    
    # Output Y-offsets (defined by footprint height)
    # The footprint height (1.7) defines the outer edges of the side waveguides.
    # Center y = (Height/2) - (w_side/2)
    y_out_offset = (footprint_height / 2) - (w_side / 2)
    
    # Calculate the vertical shift for the S-bend
    dy_bend = y_out_offset - y_in_offset

    # Cross Sections
    # We define a specific cross-section for the side arms
    xs_side = gf.cross_section.cross_section(width=w_side, layer=(1, 0))

    # --- 1. Central Taper ---
    taper = c << gf.components.taper(
        length=l_taper,
        width1=w_center,
        width2=w_tip,
        layer=(1, 0)
    )
    taper.xmin = 0
    taper.y = 0

    # --- 2. Top Waveguide Arm ---
    # Part A: Straight Section
    top_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_side
    )
    top_straight.xmin = 0
    top_straight.y = y_in_offset
    
    # Part B: S-Bend Flare
    top_bend = c << gf.components.bend_s(
        size=(l_bend, dy_bend),
        cross_section=xs_side
    )
    top_bend.connect("o1", top_straight.ports["o2"])

    # --- 3. Bottom Waveguide Arm ---
    # Part A: Straight Section
    bot_straight = c << gf.components.straight(
        length=l_straight,
        cross_section=xs_side
    )
    bot_straight.xmin = 0
    bot_straight.y = -y_in_offset
    
    # Part B: S-Bend Flare (dy is negative for downward shift)
    bot_bend = c << gf.components.bend_s(
        size=(l_bend, -dy_bend),
        cross_section=xs_side
    )
    bot_bend.connect("o1", bot_straight.ports["o2"])

    return c

# Generate and save
device = device_inverse_taper_coupler()
device.write_gds("inverse_taper_coupler.gds")
device.show()