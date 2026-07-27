import gdsfactory as gf

@gf.cell
def create_curved_coupler():
    """
    Recreates the curved directional coupler from the image.
    Footprint: 18um x 3um.
    
    Design Strategy:
    - Uses a central straight section ('waist') for a stable coupling region.
    - Uses S-bends to transition to the outer edges.
    - Uses small end-straights for clean port interfaces.
    """
    # 1. Define physical constraints
    total_width = 18.0
    total_height = 3.0
    wg_width = 1.1          # Increased for visual weight
    coupling_gap = 0.1      # Defined gap at the waist
    
    # Segment lengths for the 18um total width
    waist_len = 2.0         # Flat region in the middle
    end_straight_len = 1.5  # Straight sections at the ends
    # Remaining width for the transitions (two S-bends per arm)
    transition_dx = (total_width - waist_len - 2 * end_straight_len) / 2.0
    
    # 2. Calculate vertical positions
    # Top edge of top WG at 1.5 -> center = 1.5 - width/2
    y_edge_center = (total_height / 2.0) - (wg_width / 2.0)
    # Waist center for top WG -> center = gap/2 + width/2
    y_waist_center = (coupling_gap / 2.0) + (wg_width / 2.0)
    
    # Vertical drop for the S-bend
    dy = y_waist_center - y_edge_center
    
    # 3. Define Cross Section
    xs = gf.cross_section.strip(width=wg_width, layer=(1, 0))
    
    # 4. Create Component
    c = gf.Component("improved_curved_coupler")
    
    # 5. Build the Top Arm
    # We assemble the arm from left to right using port connections
    t_start = c << gf.components.straight(length=end_straight_len, cross_section=xs)
    t_bend_in = c << gf.components.bend_s(size=(transition_dx, dy), cross_section=xs)
    t_waist = c << gf.components.straight(length=waist_len, cross_section=xs)
    t_bend_out = c << gf.components.bend_s(size=(transition_dx, -dy), cross_section=xs)
    t_end = c << gf.components.straight(length=end_straight_len, cross_section=xs)
    
    # Connect segments
    t_bend_in.connect("o1", t_start.ports["o2"])
    t_waist.connect("o1", t_bend_in.ports["o2"])
    t_bend_out.connect("o1", t_waist.ports["o2"])
    t_end.connect("o1", t_bend_out.ports["o2"])
    
    # 6. Build the Bottom Arm (Mirror of top)
    b_start = c << gf.components.straight(length=end_straight_len, cross_section=xs)
    b_bend_in = c << gf.components.bend_s(size=(transition_dx, -dy), cross_section=xs)
    b_waist = c << gf.components.straight(length=waist_len, cross_section=xs)
    b_bend_out = c << gf.components.bend_s(size=(transition_dx, dy), cross_section=xs)
    b_end = c << gf.components.straight(length=end_straight_len, cross_section=xs)
    
    # Connect segments
    b_bend_in.connect("o1", b_start.ports["o2"])
    b_waist.connect("o1", b_bend_in.ports["o2"])
    b_bend_out.connect("o1", b_waist.ports["o2"])
    b_end.connect("o1", b_bend_out.ports["o2"])
    
    # 7. Position the arms relative to center
    # Align top arm to y_edge_center and x=0
    t_start.movey(y_edge_center)
    # The connect() calls automatically moved the rest of the top arm
    
    # Align bottom arm to -y_edge_center and x=0
    b_start.movey(-y_edge_center)
    
    # Center the entire device on (0,0)
    c.move(c.center, (0, 0))
    
    # 8. Add external ports
    c.add_port("o1", port=t_start.ports["o1"])
    c.add_port("o2", port=b_start.ports["o1"])
    c.add_port("o3", port=t_end.ports["o2"])
    c.add_port("o4", port=b_end.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = create_curved_coupler()
    component.write_gds("curved_coupler_v5.gds")
    
    # Verify footprint
    bbox = component.dbbox()
    print(f"Final Footprint: {bbox.width():.2f}um (Width) x {bbox.height():.2f}um (Height)")