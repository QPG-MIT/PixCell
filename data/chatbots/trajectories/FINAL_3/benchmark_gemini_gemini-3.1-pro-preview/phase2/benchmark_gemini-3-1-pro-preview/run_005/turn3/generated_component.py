import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Directional coupler matched to reference proportions.
    Strictly meets a 120x4 um footprint constraint.
    """
    c = gf.Component("directional_coupler")

    # Adjusted parameters for a tighter central gap and proper waveguide thickness
    width = 0.45
    gap = 0.1
    footprint_height = 4.0
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # Re-balanced horizontal lengths for smoother S-bends (derived from image ratios)
    length_total = 120.0
    length_outer = 18.0  # Increased outer port lengths
    dx_sbend = 16.0      # Increased S-bend horizontal span for smoother curves
    length_center = length_total - (2 * length_outer) - (2 * dx_sbend) # 52.0 um
    
    # Calculate precise Y-axis positions to meet the bounding box limits exactly
    y_inner = (width + gap) / 2              # 0.275 um (inner guide centers)
    y_outer = (footprint_height - width) / 2 # 1.775 um (outer guide centers)
    dy = y_outer - y_inner                   # 1.5 um (vertical span of S-bend)

    # --- 1. Primitive Generation ---
    center_str = gf.components.straight(length=length_center, cross_section=xs)
    outer_str = gf.components.straight(length=length_outer, cross_section=xs)
    
    # S-bend traversing "up" (positive dy) when moving left-to-right
    sbend_up = gf.components.bend_s(size=(dx_sbend, dy), cross_section=xs)
    # S-bend traversing "down" (negative dy) when moving left-to-right
    sbend_down = gf.components.bend_s(size=(dx_sbend, -dy), cross_section=xs)

    # --- 2. Placement & Connection ---
    
    # Center section
    c_top = c << center_str
    c_bot = c << center_str
    c_top.movey(y_inner)
    c_bot.movey(-y_inner)

    # Left side S-bends
    s_tl = c << sbend_down
    s_tl.connect("o2", c_top.ports["o1"])
    
    s_bl = c << sbend_up
    s_bl.connect("o2", c_bot.ports["o1"])

    # Right side S-bends
    s_tr = c << sbend_up
    s_tr.connect("o1", c_top.ports["o2"])
    
    s_br = c << sbend_down
    s_br.connect("o1", c_bot.ports["o2"])

    # Outer straight routing ends
    str_tl = c << outer_str
    str_tl.connect("o2", s_tl.ports["o1"])
    
    str_bl = c << outer_str
    str_bl.connect("o2", s_bl.ports["o1"])
    
    str_tr = c << outer_str
    str_tr.connect("o1", s_tr.ports["o2"])
    
    str_br = c << outer_str
    str_br.connect("o1", s_br.ports["o2"])

    # --- 3. Expose Component Ports ---
    c.add_port("o1", port=str_tl.ports["o1"])
    c.add_port("o2", port=str_bl.ports["o1"])
    c.add_port("o3", port=str_tr.ports["o2"])
    c.add_port("o4", port=str_br.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")