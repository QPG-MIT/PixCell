import gdsfactory as gf
import numpy as np

@gf.cell
def tapered_fork_geometry():
    c = gf.Component()
    
    # 1. Define Cross-Sections
    # Center: Tapers from wide to thin
    xs_c_start = gf.cross_section.cross_section(width=0.6, layer=(1, 0))
    xs_c_end = gf.cross_section.cross_section(width=0.1, layer=(1, 0))
    
    # Side: Starts thin, widens
    xs_s_start = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    xs_s_end = gf.cross_section.cross_section(width=0.6, layer=(1, 0))

    # 2. Construct Center Arm (Straight path with linear transition)
    p_center = gf.path.straight(length=40)
    t_center = gf.path.transition(xs_c_start, xs_c_end)
    center_wg = c << gf.path.extrude_transition(p_center, t_center)
    
    # 3. Construct Side Arm Path (Straight segment + Bend)
    # The path widens over the total length
    p_side = gf.path.straight(length=20) + gf.path.euler(radius=30, angle=25)
    t_side = gf.path.transition(xs_s_start, xs_s_end)
    
    # Add top arm
    top_wg = c << gf.path.extrude_transition(p_side, t_side)
    top_wg.movey(0.7)
    
    # Add bottom arm (mirrored across X-axis)
    bottom_wg = c << gf.path.extrude_transition(p_side, t_side)
    bottom_wg.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across X-axis
    bottom_wg.movey(-0.7)

    return c

# Create and save
device = tapered_fork_geometry()
device.write_gds("fork_device.gds")