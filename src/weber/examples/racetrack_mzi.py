"""
Racetrack Ring with Internal MZI

A photonic device consisting of a racetrack ring resonator with an
internal Mach-Zehnder interferometer structure.

This is an example GDSFactory script that can be processed by Weber
to generate an interactive explorer.
"""

import gdsfactory as gf


@gf.cell
def create_racetrack_mzi():
    """
    Generate a racetrack ring resonator with internal MZI.

    The device consists of:
    - Outer racetrack ring (two semicircular bends + two straight sections)
    - Internal MZI with rectangular pads
    - S-bend connectors
    - Holes in the arms for phase tuning
    """
    c = gf.Component("RacetrackMZI")
    layer_wg = (1, 0)

    # =======================================================================
    # Tunable Parameters
    # =======================================================================

    # Outer Ring
    ring_width = 0.40       # Width of ring waveguide
    r_center = 1.30         # Bend radius
    l_straight_ring = 2.50  # Length of straight sections

    # Internal MZI
    pad_w = 0.60            # Pad width
    pad_h = 0.75            # Pad height
    arm_w = 0.30            # Arm waveguide width
    arm_len = 1.70          # Arm length
    s_bend_len = 0.90       # S-bend horizontal length
    y_arm_offset = 0.54     # Vertical offset of arms from center
    y_pad_connect = 0.23    # Y position where S-bends meet pads

    # Holes (for phase tuning)
    h_w = 0.50              # Hole width
    h_h = 0.15              # Hole height
    gap_between_holes = 0.30  # Gap between hole pairs

    # =======================================================================
    # Cross Sections
    # =======================================================================
    xs_ring = gf.cross_section.cross_section(
        width=ring_width, layer=layer_wg, radius=1.0
    )
    xs_internal = gf.cross_section.cross_section(
        width=arm_w, layer=layer_wg, radius=0.1
    )

    # =======================================================================
    # Build Outer Racetrack Ring
    # =======================================================================
    straight = gf.components.straight(length=l_straight_ring, cross_section=xs_ring)
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)

    # Top and Bottom Straights
    top = c << straight
    bot = c << straight
    top.move((-l_straight_ring / 2, r_center))
    bot.move((-l_straight_ring / 2, -r_center))

    # Right Bend
    br = c << bend
    br.connect("o1", bot.ports["o2"])

    # Left Bend (Rotated 180 degrees)
    bl = c << bend
    bl.rotate(180)
    bl.connect("o1", top.ports["o1"])

    # =======================================================================
    # Build Internal MZI Structure
    # =======================================================================
    internal = gf.Component("internal")

    # Rectangular Pads
    pad_rect = gf.components.rectangle(
        size=(pad_w, pad_h), layer=layer_wg, centered=True
    )

    # Calculate X position for pads
    x_pad_dist = arm_len / 2 + s_bend_len + pad_w / 2

    pad_l = internal << pad_rect
    pad_l.move((-x_pad_dist, 0))

    pad_r = internal << pad_rect
    pad_r.move((x_pad_dist, 0))

    # Straight Arms
    arm_top = internal << gf.components.straight(
        length=arm_len, cross_section=xs_internal
    )
    arm_top.move((-arm_len / 2, y_arm_offset))

    arm_bot = internal << gf.components.straight(
        length=arm_len, cross_section=xs_internal
    )
    arm_bot.move((-arm_len / 2, -y_arm_offset))

    # S-bend Connectors
    dy_top = y_arm_offset - y_pad_connect

    # Left Side S-bends
    sb_l_t = internal << gf.components.bend_s(
        size=(s_bend_len, dy_top), cross_section=xs_internal
    )
    sb_l_t.move((pad_l.xmax, y_pad_connect))

    dy_bot = -y_arm_offset - (-y_pad_connect)
    sb_l_b = internal << gf.components.bend_s(
        size=(s_bend_len, dy_bot), cross_section=xs_internal
    )
    sb_l_b.move((pad_l.xmax, -y_pad_connect))

    # Right Side S-bends
    sb_r_t = internal << gf.components.bend_s(
        size=(s_bend_len, -dy_top), cross_section=xs_internal
    )
    sb_r_t.connect("o1", arm_top.ports["o2"])

    sb_r_b = internal << gf.components.bend_s(
        size=(s_bend_len, -dy_bot), cross_section=xs_internal
    )
    sb_r_b.connect("o1", arm_bot.ports["o2"])

    # =======================================================================
    # Create Holes (for phase tuning)
    # =======================================================================
    holes_comp = gf.Component("holes")
    hole_rect = gf.components.rectangle(
        size=(h_w, h_h), layer=layer_wg, centered=True
    )

    x_offset = h_w / 2 + gap_between_holes / 2

    # Top Arm Holes
    holes_comp.add_ref(hole_rect).move((-x_offset, y_arm_offset))
    holes_comp.add_ref(hole_rect).move((x_offset, y_arm_offset))

    # Bottom Arm Holes
    holes_comp.add_ref(hole_rect).move((-x_offset, -y_arm_offset))
    holes_comp.add_ref(hole_rect).move((x_offset, -y_arm_offset))

    # Boolean Subtraction to create holes
    internal_final = gf.boolean(internal, holes_comp, operation="not", layer=layer_wg)

    c.add_ref(internal_final)

    return c


if __name__ == "__main__":
    device = create_racetrack_mzi()
    device.write_gds("racetrack_mzi.gds")
    print("Generated racetrack_mzi.gds")

    bbox = device.bbox()
    try:
        width = bbox[1][0] - bbox[0][0]
        height = bbox[1][1] - bbox[0][1]
    except TypeError:
        width = bbox.right - bbox.left
        height = bbox.top - bbox.bottom

    print(f"Size: {width:.3f} x {height:.3f} um")
