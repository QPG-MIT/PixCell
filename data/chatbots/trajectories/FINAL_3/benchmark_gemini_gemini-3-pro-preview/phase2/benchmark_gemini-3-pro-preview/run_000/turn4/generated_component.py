import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v3():
    """
    Directional coupler with tuned proportions to match target image.
    Characteristics:
    - Footprint: 120um x 4um
    - Thicker waveguides (1.0um) for strong visual weight.
    - Narrower gap (0.15um).
    - Length distribution adjusted: shorter coupling region, longer IO straights.
    """
    c = gf.Component()

    # --- Geometric Constraints & Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    # Tuned parameters for visual matching
    wg_width = 1.0          # Thicker lines to match target visual weight
    gap = 0.15              # Very tight coupling gap
    
    # Length distribution (Total must sum to 120.0)
    # The target image shows distinct straight input arms and a coupling region
    # that occupies roughly 40-45% of the total length.
    l_io = 15.0             # Longer lead-in/lead-out straights
    l_bend = 20.0           # S-bend length
    l_coup = 50.0           # Coupling region (120 - 2*15 - 2*20 = 50)
    
    # --- Vertical Coordinate Calculations ---
    # We calculate the Y positions to utilize the full 4.0um height constraint.
    
    # 1. Input/Output Region (Outer edges at +/- 2.0um)
    # Center Y = Max_Y - (Width / 2)
    # y_io = 2.0 - 0.5 = 1.5
    y_io_top = (total_height / 2) - (wg_width / 2)
    y_io_bot = -y_io_top
    
    # 2. Coupling Region (Gap centered at 0)
    # Center Y = (Gap / 2) + (Width / 2)
    y_coup_top = (gap / 2) + (wg_width / 2)
    y_coup_bot = -y_coup_top
    
    # 3. Vertical Shift for S-Bends
    dy = y_io_top - y_coup_top  # 1.5 - 0.575 = 0.925

    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Primitives ---
    # Straight sections
    s_io = gf.components.straight(length=l_io, cross_section=xs)
    s_coup = gf.components.straight(length=l_coup, cross_section=xs)
    
    # S-Bends
    # Top Left: Moves DOWN (negative y offset)
    bend_down = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    # Top Right / Bot Left: Moves UP (positive y offset)
    bend_up = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)

    # --- Assembly ---
    
    # Top Arm Construction
    t1 = c << s_io
    t1.movey(y_io_top)
    
    t2 = c << bend_down
    t2.connect("o1", t1.ports["o2"])
    
    t3 = c << s_coup
    t3.connect("o1", t2.ports["o2"])
    
    t4 = c << bend_up
    t4.connect("o1", t3.ports["o2"])
    
    t5 = c << s_io
    t5.connect("o1", t4.ports["o2"])

    # Bottom Arm Construction
    b1 = c << s_io
    b1.movey(y_io_bot)
    
    # Bottom converges by bending UP
    b2 = c << bend_up
    b2.connect("o1", b1.ports["o2"])
    
    b3 = c << s_coup
    b3.connect("o1", b2.ports["o2"])
    
    # Bottom diverges by bending DOWN
    b4 = c << bend_down
    b4.connect("o1", b3.ports["o2"])
    
    b5 = c << s_io
    b5.connect("o1", b4.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_refined_v3()
    device.write_gds("directional_coupler_refined_v3.gds")
    device.show()