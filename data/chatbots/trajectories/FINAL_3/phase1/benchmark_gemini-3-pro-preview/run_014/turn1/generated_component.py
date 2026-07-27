import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the directional coupler device.
    Footprint: 4 um x 240 um
    """
    c = gf.Component()
    
    # 1. Define Cross Section and Dimensions
    width = 0.5
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Dimensions derived from 4um x 240um constraints
    L_total = 240.0
    H_total = 4.0
    gap_coupling = 0.2
    
    # Calculate Y coordinates (centers)
    # Inner: Center gap is 0.2, so inner edge is at 0.1. Center is at 0.1 + width/2
    y_inner = (gap_coupling + width) / 2
    # Outer: Box height is 4.0, so outer edge is at 2.0. Center is at 2.0 - width/2
    y_outer = (H_total - width) / 2
    # The vertical displacement for the S-bend
    dy = y_outer - y_inner

    # Length distribution (Sum must equal 240)
    L_io = 20.0        # Input/Output straight length
    L_coupler = 80.0   # Central coupling region length
    L_bend = (L_total - L_coupler - 2*L_io) / 2 # (240 - 80 - 40)/2 = 60.0

    # 2. Define Primitives
    # We create the specific shapes needed using the catalog functions
    
    # Straight segments
    wg_io = gf.components.straight(length=L_io, cross_section=xs)
    wg_coupler = gf.components.straight(length=L_coupler, cross_section=xs)
    
    # S-Bends
    # Top arm needs to go DOWN (-dy) to enter coupler, and UP (dy) to exit
    bend_down = gf.components.bend_s(size=(L_bend, -dy), cross_section=xs)
    bend_up = gf.components.bend_s(size=(L_bend, dy), cross_section=xs)
    
    # Bottom arm needs to go UP (dy) to enter coupler, and DOWN (-dy) to exit
    # We can reuse the same components as they are geometrically equivalent just mirrored,
    # but strictly defining them helps clarity.
    
    # 3. Assemble Top Arm
    # We create references (instances) of the components
    t_in   = c << wg_io
    t_bend1= c << bend_down
    t_mid  = c << wg_coupler
    t_bend2= c << bend_up
    t_out  = c << wg_io
    
    # Connect Top Arm Sequence
    # We use the coupling region as the anchor point (0, y_inner)
    t_mid.x = 0
    t_mid.y = y_inner
    
    # Connect outwards from center to ensure symmetry
    t_bend1.connect("o2", t_mid.ports["o1"]) # Connect end of bend to start of coupler
    t_in.connect("o2", t_bend1.ports["o1"])  # Connect end of input straight to start of bend
    
    t_bend2.connect("o1", t_mid.ports["o2"]) # Connect start of bend to end of coupler
    t_out.connect("o1", t_bend2.ports["o2"]) # Connect start of output straight to end of bend

    # 4. Assemble Bottom Arm
    b_in   = c << wg_io
    b_bend1= c << bend_up    # Goes UP into the coupler
    b_mid  = c << wg_coupler
    b_bend2= c << bend_down  # Goes DOWN out of the coupler
    b_out  = c << wg_io

    # Connect Bottom Arm Sequence
    # Anchor center
    b_mid.x = 0
    b_mid.y = -y_inner
    
    # Connect outwards
    b_bend1.connect("o2", b_mid.ports["o1"])
    b_in.connect("o2", b_bend1.ports["o1"])
    
    b_bend2.connect("o1", b_mid.ports["o2"])
    b_out.connect("o1", b_bend2.ports["o2"])

    # 5. Expose Ports
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=b_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])

    return c

# Generate and Show
if __name__ == "__main__":
    device = directional_coupler_4x240()
    device.show() # Opens in KLayout
    
    # Optional: Verify footprint
    print(f"Device Size: {device.size_info.width} x {device.size_info.height}")
    device.write_gds("directional_coupler_recreated.gds")