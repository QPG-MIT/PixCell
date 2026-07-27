import gdsfactory as gf

@gf.cell
def directional_coupler_bent():
    """
    A directional coupler consisting of two curved waveguides that come close together
    at the center.
    
    Constraints:
    - Footprint: 18.0 um x 3.0 um
    """
    c = gf.Component()

    # Dimensions derived from constraints and visual analysis
    length = 18.0
    total_height = 3.0
    
    # Geometric parameters tuned to match target image proportions
    # Width reduced to 0.85 to allow for larger gaps at the input/output
    # while staying within the 3.0um vertical limit.
    wg_width = 0.85
    
    # Minimum gap at the coupling point (waist)
    min_gap = 0.15
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate Geometric Control Points
    half_length = length / 2.0

    # --- Vertical Positioning ---
    # We calculate center-points based on the total_height and min_gap constraints
    
    # Top Waveguide Centers
    # Start: Top edge aligns with y = +1.5
    y_start_top = (total_height / 2.0) - (wg_width / 2.0)
    # Middle: Bottom edge aligns with y = +min_gap/2
    y_mid_top = (min_gap / 2.0) + (wg_width / 2.0)
    
    # Bottom Waveguide Centers (Symmetric)
    y_start_bot = -y_start_top
    y_mid_bot = -y_mid_top

    # Calculate vertical displacements (dy) for the S-bends
    dy_top = y_mid_top - y_start_top   # Negative value (going down)
    dy_bot = y_mid_bot - y_start_bot   # Positive value (going up)

    # --- Construct Top Waveguide ---
    # Left Section: Converging S-bend (Input -> Waist)
    tl = c << gf.components.bend_s(size=(half_length, dy_top), cross_section=xs)
    tl.move((0, y_start_top))

    # Right Section: Diverging S-bend (Waist -> Output)
    # We invert the dy to go back up
    tr = c << gf.components.bend_s(size=(half_length, -dy_top), cross_section=xs)
    tr.connect("o1", tl.ports["o2"])

    # --- Construct Bottom Waveguide ---
    # Left Section: Converging S-bend (Input -> Waist)
    bl = c << gf.components.bend_s(size=(half_length, dy_bot), cross_section=xs)
    bl.move((0, y_start_bot))

    # Right Section: Diverging S-bend (Waist -> Output)
    br = c << gf.components.bend_s(size=(half_length, -dy_bot), cross_section=xs)
    br.connect("o1", bl.ports["o2"])

    # --- Add External Ports ---
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_bent()
    device.write_gds("directional_coupler_bent.gds")
    device.show()