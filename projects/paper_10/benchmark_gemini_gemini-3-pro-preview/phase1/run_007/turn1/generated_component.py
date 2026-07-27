import gdsfactory as gf

@gf.cell
def racetrack_modulator():
    """
    Recreation of the racetrack device with internal heater/modulation arms.
    Target Footprint: 3.0um x 5.5um
    """
    c = gf.Component()

    # =======================================================================
    # 1. Calculate Dimensions (Constraint-driven)
    # =======================================================================
    # Footprint: Height=3.0um, Width=5.5um
    # The outer waveguide width is estimated at 0.4um.
    # Radius = (Height - Width_WG) / 2 = (3.0 - 0.4) / 2 = 1.3um
    r = 1.3
    
    # Straight Length = Width - Height = 5.5 - 3.0 = 2.5um
    l = 2.5

    # =======================================================================
    # 2. Define Cross Sections
    # =======================================================================
    # FIX: We must explicitly set 'radius' in the cross_section to 1.3.
    # This overrides the default 10.0um limit that caused the ValueError.
    xs_outer = gf.cross_section.cross_section(
        width=0.4, 
        layer=(1, 0), 
        radius=r 
    )
    
    # Inner arms are thinner
    xs_inner = gf.cross_section.cross_section(
        width=0.2, 
        layer=(1, 0)
    )

    # Internal parameters for inner arms (derived visually)
    y_inner_offset = 0.5    # Vertical offset from center y=0
    block_size = (0.7, 0.5) # Size of modulation pads
    block_spacing = 0.45    # Spacing from center x=0

    # =======================================================================
    # 3. Build Outer Racetrack Ring
    # =======================================================================
    # Create Straight Sections
    s_top = c << gf.components.straight(length=l, cross_section=xs_outer)
    s_bot = c << gf.components.straight(length=l, cross_section=xs_outer)

    # Position Straights
    # s_top: y = +r, centered horizontally
    s_top.move((-l/2, r))
    # s_bot: y = -r, centered horizontally
    s_bot.move((-l/2, -r))

    # Create Bends
    # 180 degree bends. We use the same radius 'r' defined in the cross_section.
    b_l = c << gf.components.bend_circular(radius=r, angle=180, cross_section=xs_outer)
    b_r = c << gf.components.bend_circular(radius=r, angle=180, cross_section=xs_outer)

    # Connect Bends
    # Left Bend connects to West port ("o1") of Top Straight
    # b_l starts at top, curves down.
    b_l.connect("o1", s_top.ports["o1"])

    # Right Bend connects to East port ("o2") of Bottom Straight
    # b_r starts at bottom, curves up.
    b_r.connect("o1", s_bot.ports["o2"])

    # =======================================================================
    # 4. Build Inner Arms (Modulators)
    # =======================================================================
    
    def build_inner_arm(y_center, y_connect_target):
        # Coordinates for geometry
        x_connect_left = -l/2   # X coordinate where straight meets bend
        x_connect_right = l/2
        x_inner_end = 0.8       # X extent of the straight inner rail
        
        # A. Central Rail (Path + Extrude)
        path_rail = gf.Path([(-x_inner_end, y_center), (x_inner_end, y_center)])
        c << gf.path.extrude(path_rail, cross_section=xs_inner)
        
        # B. Diagonal Connections
        # Link inner rail end to the main loop straight/bend junction
        path_link_l = gf.Path([(-x_inner_end, y_center), (x_connect_left, y_connect_target)])
        c << gf.path.extrude(path_link_l, cross_section=xs_inner)
        
        path_link_r = gf.Path([(x_inner_end, y_center), (x_connect_right, y_connect_target)])
        c << gf.path.extrude(path_link_r, cross_section=xs_inner)
        
        # C. Modulation Pads
        # Primitives like rectangle take 'layer' directly, not cross_section
        pad_l = c << gf.components.rectangle(size=block_size, layer=(1,0), centered=True)
        pad_l.move((-block_spacing, y_center))
        
        pad_r = c << gf.components.rectangle(size=block_size, layer=(1,0), centered=True)
        pad_r.move((block_spacing, y_center))

    # Build Top Arm (Connects to Top Straight at y=r)
    build_inner_arm(y_inner_offset, r)
    
    # Build Bottom Arm (Connects to Bottom Straight at y=-r)
    build_inner_arm(-y_inner_offset, -r)

    return c

if __name__ == "__main__":
    device = racetrack_modulator()
    device.write_gds("racetrack_device.gds")