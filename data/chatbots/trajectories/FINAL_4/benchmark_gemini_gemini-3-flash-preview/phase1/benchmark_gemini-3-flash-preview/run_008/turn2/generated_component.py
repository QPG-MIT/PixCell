import gdsfactory as gf

@gf.cell
def create_rail_halves(length=18.0, total_height=3.0, wg_width=0.5, center_gap=0.2):
    """
    Creates a single rail that curves from the edge to the center and back.
    """
    c = gf.Component()
    dx = length / 2
    
    # Vertical centers
    y_edge = total_height / 2 - wg_width / 2
    y_mid = center_gap / 2 + wg_width / 2
    dy = y_mid - y_edge  # Displacement to move toward the center
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Create the two S-bend segments
    # s1 curves toward the center, s2 curves back to the edge
    s1 = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    s2 = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    r1 = c << s1
    r2 = c << s2
    r2.connect("o1", r1.ports["o2"])
    
    # Export ports for assembly
    c.add_port("o1", port=r1.ports["o1"])
    c.add_port("o2", port=r2.ports["o2"])
    return c

@gf.cell
def recreate_coupler():
    """
    Assembles the point coupler using two symmetric rails.
    Footprint: 18um x 3um.
    """
    c = gf.Component("point_coupler")
    
    # Parameters matches target footprint
    length = 18.0
    total_height = 3.0
    wg_width = 0.5
    
    # Generate the base rail geometry
    rail_comp = create_rail_halves(length=length, total_height=total_height, wg_width=wg_width)
    
    # Place Top Rail
    # The rail starts at (0,0). We move it up to the edge position.
    y_offset = total_height / 2 - wg_width / 2
    top_rail = c << rail_comp
    top_rail.movey(y_offset)
    
    # Place Bottom Rail
    # We mirror the rail component itself to ensure the second half curves correctly
    bot_rail = c << rail_comp
    bot_rail.mirror_y()  # Mirrors across the rail's internal x-axis
    bot_rail.movey(-y_offset)
    
    # Add external ports
    c.add_port("o1", port=top_rail.ports["o1"])
    c.add_port("o2", port=bot_rail.ports["o1"])
    c.add_port("o3", port=top_rail.ports["o2"])
    c.add_port("o4", port=bot_rail.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = recreate_coupler()
    
    # Verification of footprint
    print(f"Component Size: {component.dxsize:.2f}um x {component.dysize:.2f}um")
    
    component.write_gds("symmetric_coupler.gds")
    component.show()