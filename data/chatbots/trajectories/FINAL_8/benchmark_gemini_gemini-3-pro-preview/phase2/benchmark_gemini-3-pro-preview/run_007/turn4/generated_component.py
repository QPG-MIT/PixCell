import gdsfactory as gf

@gf.cell
def dense_coupler_array():
    """
    Parametric recreation of the dense waveguide array.
    Method: Boolean Subtraction (Slab - Gaps).
    Creates a solid silicon block (120x4) and cuts 4 S-shaped gaps into it
    to define 5 separate waveguide regions (3 thin central stripes, 2 thick outer blocks).
    """
    c = gf.Component()

    # 1. Device Dimensions
    length = 120.0
    width = 4.0
    
    # Longitudinal Segmentation
    # The central straight section is roughly half the total length
    l_center = 60.0
    l_taper = (length - l_center) / 2  # 30.0

    # 2. Define the Mask (The Gaps)
    mask = gf.Component()
    
    # Gap Parameters
    # 0.25um width creates distinct, sharp white lines
    gap_width = 0.25 
    xs_gap = gf.cross_section.cross_section(width=gap_width, layer=(2, 0))

    # Y-coordinates for the 4 gaps (Symmetric around y=0)
    
    # Center Config (Coupling Region):
    # These coordinates create 3 roughly equal central stripes (~0.45um)
    # and leave thick outer silicon blocks.
    y_c_inner = 0.35 
    y_c_outer = 0.95
    
    # Outer Config (Port Region):
    # The gaps fan out to separate the waveguides at the inputs/outputs.
    y_o_inner = 0.7
    y_o_outer = 1.6
    
    # Lists for iteration (Top-Outer -> Top-Inner -> Bot-Inner -> Bot-Outer)
    y_center_list = [y_c_outer, y_c_inner, -y_c_inner, -y_c_outer]
    y_outer_list = [y_o_outer, y_o_inner, -y_o_inner, -y_o_outer]
    
    # Construct the paths for each gap
    for y_o, y_c in zip(y_outer_list, y_center_list):
        # A. Left Taper (S-Bend fan-in)
        # Start at left edge (-length/2, y_o) -> transition to y_c
        dy_left = y_c - y_o
        bend_left = mask << gf.components.bend_s(
            size=(l_taper, dy_left), 
            cross_section=xs_gap
        )
        bend_left.move((-length/2, y_o))
        
        # B. Center Straight Section
        # Maintains y_c for the coupling length
        straight = mask << gf.components.straight(
            length=l_center, 
            cross_section=xs_gap
        )
        straight.connect("o1", bend_left.ports["o2"])
        
        # C. Right Taper (S-Bend fan-out)
        # Transition from y_c back to y_o
        dy_right = y_o - y_c
        bend_right = mask << gf.components.bend_s(
            size=(l_taper, dy_right),
            cross_section=xs_gap
        )
        bend_right.connect("o1", straight.ports["o2"])

    # 3. Create the Main Body Slab
    # A solid block that covers the entire footprint (120x4).
    slab = gf.components.rectangle(
        size=(length, width), 
        layer=(1, 0), 
        centered=True
    )

    # 4. Apply Boolean Subtraction
    # Result = Slab (Solid) - Mask (Gaps)
    # CORRECTED: Use gf.boolean directly (top-level function)
    final_geometry = gf.boolean(
        A=slab,
        B=mask,
        operation="not",
        layer=(1, 0)
    )

    c.add_ref(final_geometry)
    return c

# Generate and save
if __name__ == "__main__":
    device = dense_coupler_array()
    device.write_gds("dense_coupler_array.gds")
    device.show()