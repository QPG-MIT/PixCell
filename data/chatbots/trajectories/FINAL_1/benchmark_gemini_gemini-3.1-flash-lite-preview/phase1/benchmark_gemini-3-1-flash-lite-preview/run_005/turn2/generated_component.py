import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    c = gf.Component()
    
    # 1. Setup Cross Sections for the transitions
    # Central taper: Wide to Narrow
    xs_center_start = gf.cross_section.cross_section(width=0.8)
    xs_center_end = gf.cross_section.cross_section(width=0.1)
    
    # Outer tapers: Narrow to Wide
    xs_outer_start = gf.cross_section.cross_section(width=0.2)
    xs_outer_end = gf.cross_section.cross_section(width=1.2)

    # 2. Central Waveguide (Straight Taper)
    path_center = gf.Path()
    path_center.append(gf.path.straight(length=40))
    
    trans_center = gf.path.transition(xs_center_start, xs_center_end, width_type='sine')
    center_wg = c << gf.path.extrude_transition(path_center, trans_center)
    center_wg.center = (20, 0) # Position in center

    # 3. Outer Waveguides (Curved Flared Tapers)
    # Define the curved path: straight segment then a flare (Euler bend)
    def get_outer_path():
        p = gf.Path()
        p.append(gf.path.straight(length=20))
        p.append(gf.path.euler(radius=50, angle=15)) # This creates the curve
        return p

    path_outer = get_outer_path()
    trans_outer = gf.path.transition(xs_outer_start, xs_outer_end, width_type='sine')
    
    # Extrude the transition along the curved path
    outer_wg = gf.path.extrude_transition(path_outer, trans_outer)
    
    # Add top waveguide
    ref_top = c << outer_wg
    ref_top.move((0, 1.2)) # Offset to create the gap
    
    # Add bottom waveguide (mirrored)
    ref_bot = c << outer_wg
    ref_bot.mirror()
    ref_bot.move((0, -1.2))

    return c

# Create and write
device = flared_coupler_device()
device.write_gds("flared_coupler.gds")