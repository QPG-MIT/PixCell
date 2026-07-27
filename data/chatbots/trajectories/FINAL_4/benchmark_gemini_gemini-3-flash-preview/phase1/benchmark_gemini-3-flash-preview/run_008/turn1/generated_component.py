import gdsfactory as gf

@gf.cell
def recreate_coupler():
    """
    Recreates the point coupler geometry from the image.
    Footprint constraint: 18um x 3um.
    """
    c = gf.Component("point_coupler")
    
    # Design Parameters based on footprint (18x3)
    length = 18.0
    total_height = 3.0
    wg_width = 0.5
    center_gap = 0.2  # Gap at the narrowest point
    
    # Derived Dimensions
    dx = length / 2
    # Vertical center of waveguides at the edges (y = +/- 1.25)
    y_edge = total_height / 2 - wg_width / 2
    # Vertical center of waveguides at the middle (y = +/- 0.35)
    y_mid = center_gap / 2 + wg_width / 2
    # The displacement for the S-bend
    dy = y_mid - y_edge 
    
    # Define the cross section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Create the S-bend primitives
    # s1 goes from edge toward center, s2 goes from center toward edge
    s1 = gf.components.bend_s(size=(dx, dy), cross_section=xs)
    s2 = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # --- Top Rail ---
    t1 = c << s1
    t2 = c << s2
    
    # Position the first segment at the top-left edge
    t1.move((0, y_edge))
    # Connect the second segment to the end of the first
    t2.connect("o1", t1.ports["o2"])
    
    # --- Bottom Rail ---
    # We can create the bottom rail by mirroring the top references
    b1 = c << s1
    b2 = c << s2
    
    # Position the bottom-left segment (mirrored vertically)
    b1.mirror_y()
    b1.move((0, -y_edge))
    # Connect the second bottom segment
    b2.connect("o1", b1.ports["o2"])
    
    # --- Define External Ports ---
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t2.ports["o2"])
    c.add_port("o4", port=b2.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create and validate component
    component = recreate_coupler()
    
    # Check footprint
    bbox = component.bbox
    print(f"Component width: {component.dxsize}um (Target: 18um)")
    print(f"Component height: {component.dysize}um (Target: 3um)")
    
    # Save and Show
    component.write_gds("recreated_device.gds")
    component.show()