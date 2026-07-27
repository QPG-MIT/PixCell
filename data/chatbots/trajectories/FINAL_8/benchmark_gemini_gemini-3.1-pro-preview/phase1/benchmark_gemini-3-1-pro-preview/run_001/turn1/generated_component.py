import gdsfactory as gf

@gf.cell
def asymmetric_coupler_array():
    """
    Creates the arrayed waveguide device with straight inner lines 
    and symmetrically flared outer cladding blocks.
    """
    c = gf.Component("asymmetric_coupler_array")
    layer = (1, 0)

    # Footprint Constraints & Overall Dimensions
    length = 120.0
    l_mid = 60.0
    l_bend = 30.0
    
    # Structural parameters derived from geometric analysis
    w = 0.1             # Width of thin waveguides
    W_thick = 0.3       # Width of the outermost thick waveguides
    gap_straight = 0.1  # Gap between waveguides in the straight center section
    gap_end = 0.17      # Gap between curved waveguides at the left/right ends
    
    p = w + gap_straight

    def add_straight_wg(y, width=0.1):
        """Helper to add a completely straight waveguide spanning the entire length."""
        xs = gf.cross_section.cross_section(width=width, layer=layer)
        wg = gf.components.straight(length=length, cross_section=xs)
        ref = c << wg
        ref.move((-length/2, y))

    def add_curved_wg(y_mid, y_end, width=0.1):
        """Helper to add a waveguide with a straight middle section and S-bends on both ends."""
        xs = gf.cross_section.cross_section(width=width, layer=layer)
        
        # Middle straight section
        wg_mid = gf.components.straight(length=l_mid, cross_section=xs)
        ref_mid = c << wg_mid
        ref_mid.move((-l_mid/2, y_mid))
        
        # Left S-bend (connects to o1 facing left, moves towards y_end at x = -60)
        dy_left = y_mid - y_end
        wg_left = gf.components.bend_s(size=(l_bend, dy_left), cross_section=xs)
        ref_left = c << wg_left
        ref_left.connect("o2", ref_mid.ports["o1"])
        
        # Right S-bend (connects to o2 facing right, moves towards y_end at x = +60)
        dy_right = y_end - y_mid
        wg_right = gf.components.bend_s(size=(l_bend, dy_right), cross_section=xs)
        ref_right = c << wg_right
        ref_right.connect("o1", ref_mid.ports["o2"])

    # 1. Add 5 central completely straight lines
    for i in range(-2, 3):
        add_straight_wg(y=i * p, width=w)

    # 2. Add Top curved lines (flare upwards at ends, merge into a solid block in the middle)
    # C1 to C4 (thin lines)
    for i in range(1, 5):
        y_mid = 0.5 + i * 0.1
        y_end = 0.4 + i * 0.27
        add_curved_wg(y_mid=y_mid, y_end=y_end, width=w)

    # C5 (thick outer line)
    add_curved_wg(y_mid=1.10, y_end=1.85, width=W_thick)

    # 3. Add Bottom curved lines (symmetric to top)
    # C1 to C4 (thin lines)
    for i in range(1, 5):
        y_mid = -(0.5 + i * 0.1)
        y_end = -(0.4 + i * 0.27)
        add_curved_wg(y_mid=y_mid, y_end=y_end, width=w)

    # C5 (thick outer line)
    add_curved_wg(y_mid=-1.10, y_end=-1.85, width=W_thick)

    return c

if __name__ == "__main__":
    # Generate the component and write it to a GDS file
    device = asymmetric_coupler_array()
    device.write_gds("asymmetric_coupler_array.gds")