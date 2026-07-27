import gdsfactory as gf

@gf.cell
def symmetric_coupler_device():
    """
    Creates a symmetric directional coupler matching the visual profile 
    and footprint [18, 3] using parametric S-bends.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Constraint: Footprint is [18, 3]
    length = 18.0
    total_height = 3.0
    
    # Estimates based on visual aspect ratio
    wg_width = 0.6
    gap_min = 0.4  # Gap at the narrowest point (center)
    
    # Calculated parameters
    l_bend = length / 2
    
    # Y-coordinates for the top waveguide center
    # At the input (widest point), the waveguide is at the top edge of the 3um box
    y_top_input = (total_height / 2) - (wg_width / 2)
    # At the center (waist), the waveguide is just above the central gap
    y_top_waist = (gap_min / 2) + (wg_width / 2)
    
    # Calculate the vertical shift (dy) required for the S-bend
    dy_drop = y_top_input - y_top_waist

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Top Waveguide Construction ---
    # 1. Top-Left: S-bend going down from input to center
    # Note: size=(x, y). y is negative for a drop.
    tl = c << gf.components.bend_s(size=(l_bend, -dy_drop), cross_section=xs)
    
    # 2. Top-Right: S-bend going up from center to output
    tr = c << gf.components.bend_s(size=(l_bend, dy_drop), cross_section=xs)
    
    # Connect Top-Right to Top-Left
    tr.connect("o1", tl.ports["o2"])
    
    # Position the Top Waveguide assembly
    # tl starts at (0,0) locally, we move it to (0, y_top_input)
    tl.move((0, y_top_input))

    # --- Bottom Waveguide Construction ---
    # 3. Bottom-Left: S-bend going up from input to center
    bl = c << gf.components.bend_s(size=(l_bend, dy_drop), cross_section=xs)
    
    # 4. Bottom-Right: S-bend going down from center to output
    br = c << gf.components.bend_s(size=(l_bend, -dy_drop), cross_section=xs)
    
    # Connect Bottom-Right to Bottom-Left
    br.connect("o1", bl.ports["o2"])
    
    # Position the Bottom Waveguide assembly
    # bl starts at (0,0) locally, we move it to (0, -y_top_input) for symmetry
    bl.move((0, -y_top_input))

    return c

# Create the component
device = symmetric_coupler_device()

# Save to GDS
device.write_gds("symmetric_coupler.gds")

# Optional: Visualize if running in a notebook/supported environment
# device.plot()