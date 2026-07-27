import gdsfactory as gf

@gf.cell
def racetrack_modulator():
    """
    Recreation of the racetrack device with internal heater/modulation arms.
    Target Footprint: 3.0um x 5.5um
    
    Adjustments from previous iteration:
    - Increased width of diagonal connectors to match outer ring.
    - Defined distinct 'Pad' geometry vs 'Wire' geometry.
    - Tuned coordinate positions for a cleaner layout.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Parameters
    # =======================================================================
    # Geometric Constants
    total_height = 3.0
    total_width = 5.5
    
    # Widths derived from visual analysis
    w_outer = 0.5       # Outer ring width
    w_diag = 0.5        # Diagonal arm width (thick, like outer ring)
    w_wire = 0.15       # Thin wire connecting the pads
    
    # Derived parameters for the Racetrack
    # Radius is from center to center-line of waveguide
    # Radius_outer_edge = 1.5. Radius_center = 1.5 - w_outer/2 = 1.25
    r_center = (total_height - w_outer) / 2  # 1.25
    
    # Length of straight section
    # L = Total Width - Height (approx approximation for racetracks)
    l_straight = total_width - total_height # 2.5
    
    # Inner Arm Parameters
    y_arm_center = 0.6        # Vertical offset for the inner arms
    pad_size = (0.6, 0.6)     # (x, y) size of the heater pads
    pad_spacing_x = 0.5       # Center X position of the pads (+/-)
    
    # Calculated X coordinates
    # The straight section of outer ring goes from -1.25 to +1.25
    x_outer_connect = l_straight / 2  # 1.25
    
    # The pads are centered at +/- 0.5. Width is 0.6.
    # Left Pad occupies x: [-0.8, -0.2]
    # Right Pad occupies x: [0.2, 0.8]
    x_pad_outer_edge = pad_spacing_x + pad_size[0]/2  # 0.8
    x_pad_inner_edge = pad_spacing_x - pad_size[0]/2  # 0.2

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=(1, 0), radius=r_center)
    xs_diag = gf.cross_section.cross_section(width=w_diag, layer=(1, 0))
    xs_wire = gf.cross_section.cross_section(width=w_wire, layer=(1, 0))

    # =======================================================================
    # 3. Build Outer Racetrack
    # =======================================================================
    # Top Straight
    s_top = c << gf.components.straight(length=l_straight, cross_section=xs_outer)
    s_top.move((-l_straight/2, r_center))
    
    # Bottom Straight
    s_bot = c << gf.components.straight(length=l_straight, cross_section=xs_outer)
    s_bot.move((-l_straight/2, -r_center))
    
    # Bends (180 degrees)
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_outer)
    
    b_left = c << bend
    b_left.connect("o1", s_top.ports["o1"])
    
    b_right = c << bend
    b_right.connect("o1", s_bot.ports["o2"])

    # =======================================================================
    # 4. Build Inner Structure
    # =======================================================================
    
    def build_arm(y_pos, y_outer_connect):
        """
        Builds one horizontal arm assembly (pads + wire + diagonals)
        y_pos: y-coordinate of the inner arm center
        y_outer_connect: y-coordinate of the outer ring connection (r_center or -r_center)
        """
        
        # 4a. Diagonal Connectors
        # Left Diagonal: From Outer-Left end of straight to Outer edge of Left Pad
        # Start point: (-x_outer_connect, y_outer_connect)
        # End point: (-x_pad_outer_edge, y_pos)
        p_diag_l = gf.Path([(-x_outer_connect, y_outer_connect), (-x_pad_outer_edge, y_pos)])
        c << gf.path.extrude(p_diag_l, cross_section=xs_diag)
        
        # Right Diagonal
        p_diag_r = gf.Path([(x_outer_connect, y_outer_connect), (x_pad_outer_edge, y_pos)])
        c << gf.path.extrude(p_diag_r, cross_section=xs_diag)
        
        # 4b. Pads
        # Left Pad
        pad_l = c << gf.components.rectangle(size=pad_size, layer=(1, 0), centered=True)
        pad_l.move((-pad_spacing_x, y_pos))
        
        # Right Pad
        pad_r = c << gf.components.rectangle(size=pad_size, layer=(1, 0), centered=True)
        pad_r.move((pad_spacing_x, y_pos))
        
        # 4c. Center Wire
        # Connects the inner edges of the two pads
        p_wire = gf.Path([(-x_pad_inner_edge, y_pos), (x_pad_inner_edge, y_pos)])
        c << gf.path.extrude(p_wire, cross_section=xs_wire)

    # Build Top Arm
    build_arm(y_arm_center, r_center)
    
    # Build Bottom Arm
    build_arm(-y_arm_center, -r_center)

    return c

if __name__ == "__main__":
    device = racetrack_modulator()
    device.write_gds("racetrack_device.gds")
    # device.show()