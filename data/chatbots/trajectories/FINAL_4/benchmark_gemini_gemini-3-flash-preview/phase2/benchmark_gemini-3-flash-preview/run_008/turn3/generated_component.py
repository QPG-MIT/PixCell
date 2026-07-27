import gdsfactory as gf

@gf.cell
def point_coupler(
    length: float = 18.0,
    total_height: float = 3.0,
    wg_width: float = 0.52,
    gap: float = 0.06,
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Creates a symmetric point coupler matching the target 18x3um footprint.
    
    Args:
        length: Total device length (um).
        total_height: Total vertical span from outer edge to outer edge (um).
        wg_width: Width of the waveguide rails (um).
        gap: Separation between waveguides at the center point (um).
        layer: GDS layer for the geometry.
    """
    c = gf.Component("symmetric_point_coupler")
    
    # Calculate vertical centers to satisfy the footprint constraint
    # Top edge of top rail at x=0 should be total_height/2
    y_edge_center = (total_height / 2) - (wg_width / 2)
    
    # Center of top rail at x=length/2 should be gap/2 + wg_width/2
    y_mid_center = (gap / 2) + (wg_width / 2)
    
    # Vertical displacement needed for the half-length S-bend
    dy = y_mid_center - y_edge_center
    half_length = length / 2
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Create the base S-bend primitives
    # s_in curves from edge toward center; s_out curves back to edge
    s_in = gf.components.bend_s(size=(half_length, dy), cross_section=xs)
    s_out = gf.components.bend_s(size=(half_length, -dy), cross_section=xs)
    
    # --- Top Rail Assembly ---
    # Place initial segment and move to top edge
    rt1 = c << s_in
    rt1.movey(y_edge_center)
    
    # Connect second segment to complete the rail
    rt2 = c << s_out
    rt2.connect("o1", rt1.ports["o2"])
    
    # --- Bottom Rail Assembly ---
    # Mirrored version of the top rail
    rb1 = c << s_in
    rb1.mirror_y()
    rb1.movey(-y_edge_center)
    
    rb2 = c << s_out
    rb2.mirror_y()
    rb2.connect("o1", rb1.ports["o2"])
    
    # Define external ports for the component
    c.add_port("o1", port=rt1.ports["o1"])
    c.add_port("o2", port=rb1.ports["o1"])
    c.add_port("o3", port=rt2.ports["o2"])
    c.add_port("o4", port=rb2.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Generate the component with the requested footprint
    component = point_coupler(length=18.0, total_height=3.0)
    
    # Verification output
    print(f"Footprint: {component.dxsize:.2f}um x {component.dysize:.2f}um")
    
    # Save and display
    component.write_gds("point_coupler.gds")
    component.show()