import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    c = gf.Component()
    
    # 1. Define Cross Sections
    # Central: Starts wide, ends very thin
    xs_center_start = gf.cross_section.cross_section(width=2.5)
    xs_center_end = gf.cross_section.cross_section(width=0.1)
    
    # Outer: Starts thin, ends wider
    xs_outer_start = gf.cross_section.cross_section(width=0.4)
    xs_outer_end = gf.cross_section.cross_section(width=2.0)

    # 2. Central Waveguide (Linear Taper)
    path_center = gf.Path()
    path_center.append(gf.path.straight(length=40))
    
    trans_center = gf.path.transition(xs_center_start, xs_center_end, width_type='sine')
    center_wg = c << gf.path.extrude_transition(path_center, trans_center)

    # 3. Outer Waveguides (Curved Flare)
    # Define the path starting at (0,0) then curving outward
    # We will position these references later using .movey()
    path_outer = gf.Path()
    path_outer.append(gf.path.straight(length=20))
    path_outer.append(gf.path.euler(radius=60, angle=25)) # Adjust radius/angle for flare intensity
    
    trans_outer = gf.path.transition(xs_outer_start, xs_outer_end, width_type='sine')
    outer_wg_geometry = gf.path.extrude_transition(path_outer, trans_outer)
    
    # Define vertical offset to maintain the gap
    # Center width (2.5) / 2 + gap (0.3) + outer start width (0.4) / 2 = 1.75
    y_offset = 1.75
    
    # Add top waveguide
    ref_top = c << outer_wg_geometry
    ref_top.movey(y_offset)
    
    # Add bottom waveguide (Mirror properly across X-axis)
    ref_bot = c << outer_wg_geometry
    ref_bot.mirror() # Mirrors across the origin (which aligns with path start)
    ref_bot.movey(-y_offset)

    return c

# Create and write
device = flared_coupler_device()
device.write_gds("flared_coupler_v2.gds")