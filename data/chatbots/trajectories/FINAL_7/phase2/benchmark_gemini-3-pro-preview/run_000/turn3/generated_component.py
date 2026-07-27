import gdsfactory as gf

@gf.cell
def racetrack_modulator():
    """
    Refined Racetrack Modulator
    - Footprint: 5.5um x 3.0um
    - Features: Hollow pad frames, smooth diagonal merging, correct aspect ratios.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Parameters
    # =======================================================================
    # -- Device Footprint --
    width_device = 5.5
    height_device = 3.0
    
    # -- Outer Ring Geometry --
    w_ring = 0.5
    # Radius is defined from center of waveguide
    r_center = (height_device - w_ring) / 2      # 1.25um
    # Length of straight section (Width - Height for standard stadium)
    l_straight = width_device - height_device    # 2.5um
    
    # -- Inner Structure Geometry --
    y_arm_offset = 0.65       # Vertical center of the inner assemblies
    
    # Pad (Hollow Frame) Dimensions
    pad_width = 0.9
    pad_height = 0.45
    pad_stroke = 0.15         # Wall thickness of the frame
    pad_gap = 0.35            # Space between left and right pads
    
    # Connectors
    w_diag = 0.5              # Width of diagonal arms (matches ring)
    w_wire = 0.15             # Width of thin central wire

    # -- Coordinate Calculations --
    # Limit of the straight section (+/- x)
    x_straight_limit = l_straight / 2  # 1.25
    
    # Pad Positioning
    # Pads are centered at x = +/- (gap/2 + width/2)
    x_pad_center = pad_gap/2 + pad_width/2
    # The outer edge of the pad (where diagonal connects)
    x_pad_outer_edge = pad_gap/2 + pad_width

    # Diagonal Connection Coordinates
    # Start Point (on Ring): We retract x slightly from the limit (1.25 -> 1.15) 
    # to ensure the thick diagonal arm merges cleanly into the straight wall 
    # and doesn't conflict with the bend start.
    x_conn_ring = x_straight_limit - 0.1
    y_conn_ring = r_center
    
    # End Point (on Pad): We extend slightly into the pad to ensure overlap
    x_conn_pad = x_pad_outer_edge - 0.1
    y_conn_pad = y_arm_offset

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    xs_ring = gf.cross_section.cross_section(width=w_ring, layer=(1, 0), radius=r_center)
    xs_diag = gf.cross_section.cross_section(width=w_diag, layer=(1, 0))
    xs_wire = gf.cross_section.cross_section(width=w_wire, layer=(1, 0))

    # =======================================================================
    # 3. Build Outer Ring
    # =======================================================================
    # Top and Bottom Straights
    s_top = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_top.move((-l_straight/2, r_center))
    
    s_bot = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_bot.move((-l_straight/2, -r_center))
    
    # Bends (180 degrees)
    # Note: radius is passed explicitly to cross_section to allow small bends
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    
    b_left = c << bend
    b_left.connect("o1", s_top.ports["o1"])
    
    b_right = c << bend
    b_right.connect("o1", s_bot.ports["o2"])

    # =======================================================================
    # 4. Build Inner Assemblies (Hollow Pads + Arms)
    # =======================================================================
    
    # Helper to create a hollow rectangular frame
    def create_pad_frame():
        # Outer rectangle
        outer = gf.components.rectangle(size=(pad_width, pad_height), layer=(1,0), centered=True)
        # Inner rectangle (hole)
        inner_w = pad_width - 2*pad_stroke
        inner_h = pad_height - 2*pad_stroke
        inner = gf.components.rectangle(size=(inner_w, inner_h), layer=(1,0), centered=True)
        # Boolean subtraction
        return gf.boolean(outer, inner, operation='not', layer=(1,0))

    pad_component = create_pad_frame()

    def build_arm_assembly(y_sign):
        """Builds the top (y_sign=1) or bottom (y_sign=-1) structure."""
        y_loc = y_sign * y_arm_offset
        y_ring_tgt = y_sign * y_conn_ring
        
        # A. Place Pads
        pl = c << pad_component
        pl.move((-x_pad_center, y_loc))
        
        pr = c << pad_component
        pr.move((x_pad_center, y_loc))
        
        # B. Central Wire (connecting the two pads)
        wire_path = gf.Path([(-pad_gap/2, y_loc), (pad_gap/2, y_loc)])
        c << gf.path.extrude(wire_path, cross_section=xs_wire)
        
        # C. Diagonal Arms
        # Left Diagonal: Outer Ring Left -> Left Pad Left Edge
        diag_l_path = gf.Path([(-x_conn_ring, y_ring_tgt), (-x_conn_pad, y_loc)])
        c << gf.path.extrude(diag_l_path, cross_section=xs_diag)
        
        # Right Diagonal: Outer Ring Right -> Right Pad Right Edge
        diag_r_path = gf.Path([(x_conn_ring, y_ring_tgt), (x_conn_pad, y_loc)])
        c << gf.path.extrude(diag_r_path, cross_section=xs_diag)

    # Construct Top Assembly
    build_arm_assembly(1)
    
    # Construct Bottom Assembly
    build_arm_assembly(-1)

    return c

if __name__ == "__main__":
    device = racetrack_modulator()
    device.write_gds("racetrack_device.gds")
    # device.show()