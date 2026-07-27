import gdsfactory as gf

@gf.cell
def racetrack_modulator():
    """
    Racetrack Modulator Reconstruction
    Footprint: 5.5um x 3.0um
    Features: Hollow pad frames, aligned diagonal connectors, specific widths.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Parameters
    # =======================================================================
    # -- Device Constraints --
    width_device = 5.5
    height_device = 3.0
    
    # -- Outer Ring Geometry --
    w_ring = 0.5
    # Radius from center to waveguide center
    r_center = (height_device - w_ring) / 2    # 1.25um
    # Length of straight section
    l_straight = width_device - height_device  # 2.5um
    
    # -- Inner Structure Geometry --
    # Adjusted based on visual analysis of gaps and fills
    y_offset = 0.6             # Vertical center position of the pads
    h_pad = 0.55               # Height of the hollow pad frame
    w_pad = 0.85               # Width of the hollow pad frame
    w_stroke = 0.18            # Thickness of the frame walls
    gap_pads = 0.4             # Horizontal gap between the left and right pads
    
    w_diag = 0.35              # Width of diagonal connector (thinner than ring)
    w_wire = 0.12              # Width of the thin central wire
    
    # -- Coordinate Calculations --
    # Pad X positions
    x_pad_center = gap_pads/2 + w_pad/2
    x_pad_inner_edge = gap_pads/2
    x_pad_outer_edge = gap_pads/2 + w_pad
    
    # Ring Connection Point X
    # Connect slightly before the bend starts to ensure clean boolean union
    x_ring_connect = l_straight/2 - 0.15 

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    xs_ring = gf.cross_section.cross_section(width=w_ring, layer=(1, 0), radius=r_center)
    xs_diag = gf.cross_section.cross_section(width=w_diag, layer=(1, 0))
    xs_wire = gf.cross_section.cross_section(width=w_wire, layer=(1, 0))

    # =======================================================================
    # 3. Build Outer Ring
    # =======================================================================
    # Top Straight
    s_top = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_top.move((-l_straight/2, r_center))
    
    # Bottom Straight
    s_bot = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_bot.move((-l_straight/2, -r_center))
    
    # Bends (180 degree circular arcs)
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    
    bl = c << bend
    bl.connect("o1", s_top.ports["o1"])
    
    br = c << bend
    br.connect("o1", s_bot.ports["o2"])

    # =======================================================================
    # 4. Build Inner Assemblies
    # =======================================================================
    
    # Helper to create the hollow rectangular frame shape
    def create_pad_shape():
        outer = gf.components.rectangle(size=(w_pad, h_pad), layer=(1,0), centered=True)
        # Inner void size
        inner_w = w_pad - 2*w_stroke
        inner_h = h_pad - 2*w_stroke
        inner = gf.components.rectangle(size=(inner_w, inner_h), layer=(1,0), centered=True)
        # Subtract inner from outer
        return gf.boolean(outer, inner, 'not', layer=(1,0))

    # Create the reusable pad geometry
    pad_shape = create_pad_shape()

    def build_assembly(y_sign):
        """
        Constructs one arm assembly.
        y_sign: +1 for Top, -1 for Bottom
        """
        y_loc = y_sign * y_offset
        
        # A. Add Pads
        pl = c << pad_shape
        pl.move((-x_pad_center, y_loc))
        
        pr = c << pad_shape
        pr.move((x_pad_center, y_loc))
        
        # B. Add Central Wire
        # Connects the inner edges of the two pads
        wire_path = gf.Path([(-x_pad_inner_edge, y_loc), (x_pad_inner_edge, y_loc)])
        c << gf.path.extrude(wire_path, cross_section=xs_wire)
        
        # C. Add Diagonal Connectors
        # Logic: Align the "outer" edge of the diagonal arm with the "outer" edge of the pad.
        # This creates the continuous flat top/bottom profile seen in the image.
        
        # Calculate Y-offset to align edges:
        # Distance from Center of Pad to Top Edge = h_pad/2
        # Distance from Center of Diag to Top Edge = w_diag/2
        # Shift = h_pad/2 - w_diag/2
        dy = y_sign * (h_pad/2 - w_diag/2)
        y_diag_at_pad = y_loc + dy
        
        # Target Y at Ring (Connect to center of waveguide for robust union)
        y_diag_at_ring = y_sign * r_center
        
        # Right Diagonal
        # Start slightly inside the pad (x_pad_outer_edge - 0.1) for overlap
        p_dr = gf.Path([(x_pad_outer_edge - 0.1, y_diag_at_pad), (x_ring_connect, y_diag_at_ring)])
        c << gf.path.extrude(p_dr, cross_section=xs_diag)
        
        # Left Diagonal
        p_dl = gf.Path([(-x_pad_outer_edge + 0.1, y_diag_at_pad), (-x_ring_connect, y_diag_at_ring)])
        c << gf.path.extrude(p_dl, cross_section=xs_diag)

    # Build Top Assembly
    build_assembly(1)
    
    # Build Bottom Assembly
    build_assembly(-1)

    return c

if __name__ == "__main__":
    device = racetrack_modulator()
    device.write_gds("racetrack_device.gds")