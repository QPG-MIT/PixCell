import gdsfactory as gf

@gf.cell
def symmetric_curved_coupler() -> gf.Component:
    """
    Creates a symmetric curved directional coupler out of continuous S-bends.
    Footprint constrained to exactly 18um x 3um.
    """
    c = gf.Component()
    
    # Adjusted waveguide cross-section based on visual proportions
    # 0.8um wg_width gives the thick, bold look from the target image
    wg_width = 0.8
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Constraints (Footprint: 18x3)
    L_total = 18.0
    H_total = 3.0
    gap = 0.2  # Tighter gap visually matched to the target image
    
    # Derived geometric parameters
    # Splitting the total length perfectly in half for two back-to-back S-bends
    L_sbend = L_total / 2.0
    
    # Outer Y coordinate (center of wg) to make outer bounding edge exactly at +/- H_total / 2
    y_center_end = (H_total / 2.0) - (wg_width / 2.0)
    
    # Inner Y coordinate (center of wg) to achieve the desired coupling gap at the center
    y_center_mid = (gap / 2.0) + (wg_width / 2.0)

    # Vertical transition height for a single S-bend
    dy = y_center_end - y_center_mid

    # ====================
    # TOP ARM
    # ====================
    # Top-Left S-bend: Starts at y_center_end, smoothly dips downwards by dy
    top_sbend1 = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    top_sbend1.move((0, y_center_end))

    # Top-Right S-bend: Connects to the center dip, smoothly curves back up by dy
    top_sbend2 = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    top_sbend2.connect("o1", top_sbend1.ports["o2"])

    # ====================
    # BOTTOM ARM
    # ====================
    # Bottom-Left S-bend: Starts at -y_center_end, smoothly rises upwards by dy
    bot_sbend1 = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    bot_sbend1.move((0, -y_center_end))

    # Bottom-Right S-bend: Connects to the center peak, smoothly curves back down by dy
    bot_sbend2 = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    bot_sbend2.connect("o1", bot_sbend1.ports["o2"])

    # ====================
    # EXPOSE PORTS
    # ====================
    c.add_port("o1", port=top_sbend1.ports["o1"])
    c.add_port("o2", port=bot_sbend1.ports["o1"])
    c.add_port("o3", port=top_sbend2.ports["o2"])
    c.add_port("o4", port=bot_sbend2.ports["o2"])

    return c

# Generate and save the geometry to a GDS file
if __name__ == "__main__":
    coupler_device = symmetric_curved_coupler()
    coupler_device.write_gds("symmetric_curved_coupler.gds")