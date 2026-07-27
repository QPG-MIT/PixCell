import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Directional coupler composed of straight and S-bend primitives.
    Designed to meet a strict 120x4 um footprint.
    """
    c = gf.Component()

    # Define standard cross-section
    width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # Geometry parameters to precisely meet the [120, 4] footprint
    length_total = 120.0
    length_outer = 10.0
    dx_sbend = 20.0
    length_center = length_total - (2 * length_outer) - (2 * dx_sbend) # 60.0
    
    gap = 0.2
    port_separation = 3.5  # Yields exactly 4um total footprint height with 0.5um width

    # Calculate Y-axis positions
    y_inner = (width + gap) / 2      # 0.35 um (center of inner coupling guides)
    y_outer = port_separation / 2    # 1.75 um (center of outer routing guides)
    dy = y_outer - y_inner           # 1.4 um (S-bend vertical shift)

    # --- 1. Center Straight Coupling Region ---
    center_top = c << gf.components.straight(length=length_center, cross_section=xs)
    center_bot = c << gf.components.straight(length=length_center, cross_section=xs)

    # Position the central region waveguides
    center_top.movey(y_inner)
    center_bot.movey(-y_inner)

    # --- 2. S-bends ---
    # Top left: traverses from outer height down to inner height (negative dy)
    sbend_tl = c << gf.components.bend_s(size=(dx_sbend, -dy), cross_section=xs)
    # Bottom left: traverses from outer depth up to inner depth (positive dy)
    sbend_bl = c << gf.components.bend_s(size=(dx_sbend, dy), cross_section=xs)

    # Top right: traverses from inner height up to outer height (positive dy)
    sbend_tr = c << gf.components.bend_s(size=(dx_sbend, dy), cross_section=xs)
    # Bottom right: traverses from inner depth down to outer depth (negative dy)
    sbend_br = c << gf.components.bend_s(size=(dx_sbend, -dy), cross_section=xs)

    # Connect S-bends to the central coupling region
    sbend_tl.connect("o2", center_top.ports["o1"])
    sbend_bl.connect("o2", center_bot.ports["o1"])
    
    sbend_tr.connect("o1", center_top.ports["o2"])
    sbend_br.connect("o1", center_bot.ports["o2"])

    # --- 3. Outer Straight Routing Ends ---
    str_tl = c << gf.components.straight(length=length_outer, cross_section=xs)
    str_bl = c << gf.components.straight(length=length_outer, cross_section=xs)
    str_tr = c << gf.components.straight(length=length_outer, cross_section=xs)
    str_br = c << gf.components.straight(length=length_outer, cross_section=xs)

    # Connect the outer straight routing extensions to the S-Bends
    str_tl.connect("o2", sbend_tl.ports["o1"])
    str_bl.connect("o2", sbend_bl.ports["o1"])
    
    str_tr.connect("o1", sbend_tr.ports["o2"])
    str_br.connect("o1", sbend_br.ports["o2"])

    # --- 4. Expose Component Ports ---
    c.add_port("o1", port=str_tl.ports["o1"])
    c.add_port("o2", port=str_bl.ports["o1"])
    c.add_port("o3", port=str_tr.ports["o2"])
    c.add_port("o4", port=str_br.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler()
    # Added the required line to produce the GDS file
    device.write_gds("directional_coupler.gds")