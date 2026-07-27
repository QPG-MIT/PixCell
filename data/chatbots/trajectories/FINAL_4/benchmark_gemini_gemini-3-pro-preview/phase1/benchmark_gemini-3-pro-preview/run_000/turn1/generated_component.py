import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic directional coupler using S-bends.
    Based on a device footprint of 18um x 3um.
    """
    c = gf.Component()
    
    # 1. Define Geometric Constraints
    length = 18.0
    total_height = 3.0
    wg_width = 0.5          # Standard waveguide width
    min_gap = 0.4           # Estimated gap at the narrowest point (waist)
    
    # 2. Derive Coordinates
    # Calculate Y-coordinates for the waveguide centers
    
    # At the input/output ports (widest separation):
    # Assuming the device occupies the full 3um height, outer edges are at y=+1.5 and y=-1.5.
    # Center y = Edge y - (width/2)
    y_in_top = (total_height / 2) - (wg_width / 2)   # y = 1.25
    y_in_bot = -y_in_top                             # y = -1.25
    
    # At the waist (narrowest separation):
    y_waist_top = (min_gap / 2) + (wg_width / 2)
    y_waist_bot = -y_waist_top
    
    # Dimensions for the S-bend primitives
    # The device is symmetric, so each bend covers half the length
    sbend_length = length / 2
    
    # Vertical displacement (dy) for the converging section
    # For top arm: goes from 1.25 down to waist. dy is negative.
    dy_converge = y_waist_top - y_in_top 
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width)

    # 3. Construct Geometry
    
    # --- Top Arm ---
    # Part 1: Converge (Input -> Waist)
    # bend_s connects (0,0) to (x, y). We move it to start at the input height.
    t_in = c << gf.components.bend_s(size=(sbend_length, dy_converge), cross_section=xs)
    t_in.movey(y_in_top)
    
    # Part 2: Diverge (Waist -> Output)
    # To go back up, dy is positive (-dy_converge)
    t_out = c << gf.components.bend_s(size=(sbend_length, -dy_converge), cross_section=xs)
    t_out.connect("o1", t_in.ports["o2"])
    
    # --- Bottom Arm ---
    # Part 1: Converge (Input -> Waist)
    # Bottom arm moves UP to converge, so dy is positive (-dy_converge)
    b_in = c << gf.components.bend_s(size=(sbend_length, -dy_converge), cross_section=xs)
    b_in.movey(y_in_bot)
    
    # Part 2: Diverge (Waist -> Output)
    # Bottom arm moves DOWN to diverge, so dy is negative (dy_converge)
    b_out = c << gf.components.bend_s(size=(sbend_length, dy_converge), cross_section=xs)
    b_out.connect("o1", b_in.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=t_in.ports["o1"])   # Top Left
    c.add_port("o2", port=b_in.ports["o1"])   # Bottom Left
    c.add_port("o3", port=t_out.ports["o2"])  # Top Right
    c.add_port("o4", port=b_out.ports["o2"])  # Bottom Right

    return c

# Create and save the GDS file
if __name__ == "__main__":
    device = adiabatic_coupler()
    device.write_gds("adiabatic_coupler.gds")
    device.show()