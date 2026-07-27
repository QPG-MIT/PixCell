import gdsfactory as gf

@gf.cell
def symmetric_curved_coupler() -> gf.Component:
    """
    Creates a symmetric curved directional coupler out of S-bends.
    Footprint constrained to exactly 18um x 3um.
    """
    c = gf.Component()
    
    # Adjusted waveguide cross-section based on visual proportions
    wg_width = 0.6  # Increased from 0.5 to better match image
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Constraints (Footprint: 18x3)
    L_total = 18.0
    H_total = 3.0
    gap = 0.5  # Increased from 0.2 to widen the center separation

    # Derived geometric parameters to meet the exact bounding footprint
    L_half = L_total / 2.0
    
    # Outer Y coordinate (center of wg) to make outer bounding edge exactly at H_total / 2
    y_outer = (H_total / 2.0) - (wg_width / 2.0)
    
    # Inner Y coordinate (center of wg) to achieve the desired coupling gap at the center
    y_inner = (gap / 2.0) + (wg_width / 2.0)

    # Vertical transition height for a single S-bend
    dy = y_outer - y_inner

    # ====================
    # TOP ARM
    # ====================
    # Top-Left: Starts at y_outer, smoothly dips downwards
    top_left = c << gf.components.bend_s(size=(L_half, -dy), cross_section=xs)
    top_left.move((0, y_outer))

    # Top-Right: Connects to center dip, smoothly curves back up to y_outer
    top_right = c << gf.components.bend_s(size=(L_half, dy), cross_section=xs)
    top_right.connect("o1", top_left.ports["o2"])

    # ====================
    # BOTTOM ARM
    # ====================
    # Bottom-Left: Starts at -y_outer, smoothly rises upwards
    bot_left = c << gf.components.bend_s(size=(L_half, dy), cross_section=xs)
    bot_left.move((0, -y_outer))

    # Bottom-Right: Connects to center peak, smoothly curves back down to -y_outer
    bot_right = c << gf.components.bend_s(size=(L_half, -dy), cross_section=xs)
    bot_right.connect("o1", bot_left.ports["o2"])

    # ====================
    # EXPOSE PORTS
    # ====================
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])

    return c

# Generate and save the geometry to a GDS file
if __name__ == "__main__":
    coupler_device = symmetric_curved_coupler()
    coupler_device.write_gds("symmetric_curved_coupler.gds")