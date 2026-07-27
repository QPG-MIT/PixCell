import gdsfactory as gf

@gf.cell
def tapered_fork_geometry():
    c = gf.Component()

    # 1. Define the cross-sections for the transitions
    # Center: wide to narrow
    xs_center_start = gf.cross_section.cross_section(width=0.6, layer=(1, 0))
    xs_center_end = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    
    # Outer arms: narrow to wide (and curved)
    xs_side_start = gf.cross_section.cross_section(width=0.1, layer=(1, 0))
    xs_side_end = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Construct the Center Path (Straight)
    # Using straight path + transition for the tapering effect
    p_center = gf.path.straight(length=40)
    t_center = gf.path.transition(xs_center_start, xs_center_end)
    center_wg = gf.path.extrude_transition(p_center, t_center)
    c.add_ref(center_wg)

    # 3. Construct the Outer Paths (Curved)
    # Using euler curves for smooth adiabatic transitions
    p_side = gf.path.euler(radius=50, angle=10) + gf.path.straight(length=30)
    t_side = gf.path.transition(xs_side_start, xs_side_end)
    side_wg = gf.path.extrude_transition(p_side, t_side)

    # 4. Position Top and Bottom arms
    # Add top arm
    top = c << side_wg
    top.movey(0.55) # Vertical offset
    
    # Add bottom arm (mirrored)
    bottom = c << side_wg
    bottom.mirror_y() 
    bottom.movey(-0.55)

    return c

# Create and save
device = tapered_fork_geometry()
device.write_gds("fork_device.gds")