import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    c = gf.Component()
    
    # 1. Define Cross Sections
    # Central: Tapers from 0.8um to 2.8um
    xs_center_start = gf.cross_section.cross_section(width=0.8)
    xs_center_end = gf.cross_section.cross_section(width=2.8)
    
    # Outer: Tapers from 0.4um to 1.5um
    xs_outer_start = gf.cross_section.cross_section(width=0.4)
    xs_outer_end = gf.cross_section.cross_section(width=1.5)

    # 2. Central Waveguide (Straight Taper)
    path_center = gf.Path()
    path_center.append(gf.path.straight(length=40))
    
    trans_center = gf.path.transition(xs_center_start, xs_center_end, width_type='sine')
    center_wg = c << gf.path.extrude_transition(path_center, trans_center)

    # 3. Outer Waveguides (Gentle Flare)
    # Reducing angle (10 deg) and increasing radius (50um) to create a subtle flare
    path_outer = gf.Path()
    path_outer.append(gf.path.euler(radius=50, angle=10)) 
    
    trans_outer = gf.path.transition(xs_outer_start, xs_outer_end, width_type='sine')
    outer_wg_geometry = gf.path.extrude_transition(path_outer, trans_outer)
    
    # Calculate vertical offset to maintain a tight gap at the start
    # Center start (0.8)/2 + Gap (0.2) + Outer start (0.4)/2 = 0.8
    y_offset = 0.8
    
    # Add top waveguide
    ref_top = c << outer_wg_geometry
    ref_top.movey(y_offset)
    
    # Add bottom waveguide
    ref_bot = c << outer_wg_geometry
    ref_bot.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis
    ref_bot.movey(-y_offset)

    return c

# Create and write
device = flared_coupler_device()
device.write_gds("flared_coupler_v3.gds")