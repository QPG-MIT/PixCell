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

    # Dimensions derived from constraints
    length = 18.0
    total_height = 3.0
    
    # Parameters tuned to match the target image proportions
    wg_width = 0.9      # Slightly thicker to match the visual weight of the black lines
    min_gap = 0.2       # Gap at the waist (interaction region)
    
    # We introduce a short straight section in the middle to replicate the 
    # smooth, flat interaction region seen in the target image.
    coupling_length = 2.0 
    
    # The remaining length is split between the input and output S-bends
    bend_length = (length - coupling_length) / 2.0

    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Vertical Calculations ---
    # We calculate positions to ensure the total bounding box is exactly 3.0 um high.
    
    # Top Waveguide:
    # Start: Top edge aligns with y = +1.5
    y_top_start = (total_height / 2.0) - (wg_width / 2.0)
    # Waist: Bottom edge aligns with y = +min_gap/2
    y_top_waist = (min_gap / 2.0) + (wg_width / 2.0)
    
    # Vertical travel distance for the S-bend (negative value as it goes down)
    dy = y_top_waist - y_top_start

    # --- Top Waveguide Construction ---
    # 1. Converging S-bend (Input -> Waist)
    tl = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    tl.move((0, y_top_start))

    # 2. Straight Coupling Region (Waist)
    # This creates the flat, parallel region in the center
    tm = c << gf.components.straight(length=coupling_length, cross_section=xs)
    tm.connect("o1", tl.ports["o2"])

    # 3. Diverging S-bend (Waist -> Output)
    # Note: -dy is positive, bringing the waveguide back up
    tr = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs)
    tr.connect("o1", tm.ports["o2"])

    # --- Bottom Waveguide Construction (Symmetric) ---
    y_bot_start = -y_top_start
    
    # 1. Converging S-bend (Input -> Waist)
    # dy is inverted relative to top (goes up)
    bl = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs)
    bl.move((0, y_bot_start))

    # 2. Straight Coupling Region
    bm = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bm.connect("o1", bl.ports["o2"])

    # 3. Diverging S-bend (Waist -> Output)
    br = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    br.connect("o1", bm.ports["o2"])

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