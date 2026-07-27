import gdsfactory as gf

@gf.cell
def symmetric_coupler_recreated():
    """
    Recreates the symmetric curved coupler.
    Total footprint constraint: 18um x 3um.
    """
    c = gf.Component("symmetric_coupler")
    
    # 1. Geometric Parameters
    # Total width is 18um. Each S-bend covers half (9um).
    width = 0.6
    total_length = 18.0
    half_length = total_length / 2
    
    # Vertical separation between ports (center-to-center)
    port_sep = 1.8 
    # Vertical dip for each 9um segment to reach the coupling region
    dip_depth = 0.5 
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Construct the Top Arm (Dips down then up)
    # Part 1: Starts at (0, 0), ends at (9, -0.5)
    t1_ref = c << gf.components.bend_s(size=(half_length, -dip_depth), cross_section=xs)
    # Part 2: Starts at (0, 0), ends at (9, +0.5). We move it to start at (9, -0.5)
    t2_ref = c << gf.components.bend_s(size=(half_length, dip_depth), cross_section=xs)
    t2_ref.move((half_length, -dip_depth))
    
    # 3. Construct the Bottom Arm (Dips up then down)
    # We shift the whole arm starting position by -port_sep vertically
    # Part 1: Starts at (0, -1.8), ends at (9, -1.8 + 0.5 = -1.3)
    b1_ref = c << gf.components.bend_s(size=(half_length, dip_depth), cross_section=xs)
    b1_ref.movey(-port_sep)
    
    # Part 2: Starts at (0, 0), ends at (9, -0.5). We move it to start at (9, -1.3)
    b2_ref = c << gf.components.bend_s(size=(half_length, -dip_depth), cross_section=xs)
    b2_ref.move((half_length, -port_sep + dip_depth))
    
    # 4. Define Ports
    c.add_port("o1", port=t1_ref.ports["o1"])
    c.add_port("o2", port=b1_ref.ports["o1"])
    c.add_port("o3", port=t2_ref.ports["o2"])
    c.add_port("o4", port=b2_ref.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = symmetric_coupler_recreated()
    
    # CORRECT WAY TO GET SIZE in KFactory-based GDSFactory:
    # Use the dbbox (database bounding box) which returns coordinates in microns.
    bbox = component.dbbox()
    width_um = bbox.width()
    height_um = bbox.height()
    
    print(f"Generated device dimensions: {width_um:.2f}um x {height_um:.2f}um")
    
    # Export and show
    component.write_gds("symmetric_coupler_fixed.gds")
    component.show()