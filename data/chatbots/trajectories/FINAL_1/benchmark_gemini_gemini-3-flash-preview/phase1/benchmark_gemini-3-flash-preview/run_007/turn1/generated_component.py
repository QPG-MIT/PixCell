import gdsfactory as gf

@gf.cell
def jaw_harp_resonator():
    """
    Recreates the jaw-harp geometry from the image.
    Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component()
    
    # Target dimensions
    TOTAL_LENGTH = 40.0
    TOTAL_HEIGHT = 1.7
    LAYER = (1, 0)
    
    # 1. CENTRAL TONGUE
    # The tongue consists of a short straight base and a long taper.
    w_tongue_base = 0.45
    w_tongue_tip = 0.10
    l_tongue_straight = 4.0
    l_tongue_taper = 21.0
    
    # Base segment
    xs_tongue_base = gf.cross_section.cross_section(width=w_tongue_base, layer=LAYER)
    t_straight = c << gf.components.straight(length=l_tongue_straight, cross_section=xs_tongue_base)
    t_straight.xmin = 0
    t_straight.y = 0
    
    # Tapered segment
    t_taper = c << gf.components.taper(length=l_tongue_taper, width1=w_tongue_base, width2=w_tongue_tip, layer=LAYER)
    t_taper.connect("o1", t_straight.ports["o2"])
    
    # 2. OUTER ARMS
    # The arms start at the same x-coordinate as the tongue's taper.
    # They taper from narrow to wide and flare outwards.
    w_arm_start = 0.18
    w_arm_end = 0.45
    gap_start = 0.10
    
    # Vertical positions for path centerlines
    # Start: (tongue half-width) + gap + (arm half-width)
    y_start = (w_tongue_base / 2) + gap_start + (w_arm_start / 2)
    # End: (total height / 2) - (arm end half-width) to reach exactly 1.7um total height
    y_end = (TOTAL_HEIGHT / 2) - (w_arm_end / 2)
    
    # Define points for the top arm path
    # (Straight section, followed by a smooth flare-out)
    pts = [
        (l_tongue_straight, y_start),
        (22.0, y_start),
        (33.0, y_end),
        (TOTAL_LENGTH, y_end)
    ]
    arm_path = gf.path.smooth(points=pts, radius=6.0)
    
    # Define width transition for the arms (tapering from 0.18 to 0.45 um)
    xs_start = gf.cross_section.cross_section(width=w_arm_start, layer=LAYER)
    xs_end = gf.cross_section.cross_section(width=w_arm_end, layer=LAYER)
    arm_transition = gf.path.transition(xs_start, xs_end, width_type="linear")
    
    # Add top and bottom (mirrored) arms
    arm_top = c << gf.path.extrude_transition(arm_path, transition=arm_transition)
    arm_bottom = c << gf.path.extrude_transition(arm_path, transition=arm_transition)
    arm_bottom.mirror_y()
    
    return c

if __name__ == "__main__":
    # Create the component
    component = jaw_harp_resonator()
    
    # Save/Show
    component.show()
    component.write_gds("jaw_harp_resonator.gds")