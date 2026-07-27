import gdsfactory as gf

@gf.cell
def mzi_racetrack_resonator():
    """
    Generates a racetrack ring resonator with internal S-bends and 
    structured straight arms containing rectangular heater/modulator pads.
    
    Target Footprint: ~5.5um x 3.0um
    """
    c = gf.Component()

    # =========================================================================
    # 1. Dimensions & Parameters
    # =========================================================================
    
    # Geometry derivation from 3.0um height and 5.5um width constraints
    R = 1.35 
    
    # Widths
    width_wg = 0.2    # Thin waveguide width
    width_pad = 0.65  # Wide pad width for the straight segments
    
    # Vertical Offsets
    # The arms are pulled inwards relative to the 180-degree bends. 
    # y_outer: Y-coordinate of the bend ports (relative to center axis)
    # y_inner: Y-coordinate of the straight arm axis
    y_outer = R
    y_inner = 0.5
    dy = y_inner - y_outer # approx -0.85um (displacement for S-bend)

    # Lengths for the straight section components
    len_sbend = 0.55
    len_pad = 0.55
    len_gap = 0.4
    
    # =========================================================================
    # 2. Cross Sections (FIXED)
    # =========================================================================
    # We set radius_min=0.1 to allow the tight S-bends (~0.125um radius)
    # required by the compact geometry.
    
    xs_wg = gf.cross_section.cross_section(
        width=width_wg, 
        radius=R,
        radius_min=0.1, 
        layer=(1, 0)
    )
    
    xs_pad = gf.cross_section.cross_section(
        width=width_pad,
        radius=R,
        radius_min=0.1,
        layer=(1, 0)
    )

    # =========================================================================
    # 3. Sub-Component Definitions
    # =========================================================================

    def arm_structure():
        """Creates the Pad-Gap-Pad straight sequence."""
        cmp = gf.Component()
        # First Pad
        p1 = cmp << gf.components.straight(length=len_pad, cross_section=xs_pad)
        # Narrow Gap
        g  = cmp << gf.components.straight(length=len_gap, cross_section=xs_wg)
        # Second Pad
        p2 = cmp << gf.components.straight(length=len_pad, cross_section=xs_pad)
        
        # Connect sequentially
        g.connect("o1", p1.ports["o2"])
        p2.connect("o1", g.ports["o2"])
        
        # Expose ports
        cmp.add_port("o1", port=p1.ports["o1"])
        cmp.add_port("o2", port=p2.ports["o2"])
        return cmp

    # =========================================================================
    # 4. Assembly
    # =========================================================================

    # --- Left Bend ---
    # Create a 180 degree bend.
    # Standard orientation: o1 at (0,0), o2 at (0, 2R).
    # We rotate it 180 degrees so the arc bulges Left.
    # New orientation: o2 is at bottom, o1 is at top.
    bend_left = c << gf.components.bend_circular(radius=R, angle=180, cross_section=xs_wg)
    bend_left.rotate(180)
    
    # --- Top Arm Construction (Left -> Right) ---
    
    # 1. S-Bend Down: Transition from outer radius R to inner track y=0.5
    # The bend port is at Y=R. We need to get to Y=0.5. dy is negative.
    sb_top_in = c << gf.components.bend_s(size=(len_sbend, dy), cross_section=xs_wg)
    sb_top_in.connect("o1", bend_left.ports["o2"]) 
    
    # 2. Arm Structure (Pads)
    arm_top = c << arm_structure()
    arm_top.connect("o1", sb_top_in.ports["o2"])
    
    # 3. S-Bend Up: Transition from inner track y=0.5 back to outer radius R
    # displacement is positive (-dy)
    sb_top_out = c << gf.components.bend_s(size=(len_sbend, -dy), cross_section=xs_wg)
    sb_top_out.connect("o1", arm_top.ports["o2"])
    
    # --- Right Bend ---
    # Standard 180 bend fits perfectly here to close the right side.
    # Connects Top Arm Output -> Bottom Arm Input
    bend_right = c << gf.components.bend_circular(radius=R, angle=180, cross_section=xs_wg)
    bend_right.connect("o2", sb_top_out.ports["o2"])
    
    # --- Bottom Arm Construction (Right -> Left) ---
    # We build the bottom path flowing from Right Bend to Left Bend.
    # We rotate components 180 degrees to handle the Westward flow.
    
    # 1. S-Bend In (Right Side): Outer -> Inner
    # Rotating 180 means we are building backwards (Right to Left).
    # To shift "In" (towards center) on the bottom, we need to go UP (+y) geometrically.
    # Shift = +0.85 = -dy.
    sb_bot_in = c << gf.components.bend_s(size=(len_sbend, -dy), cross_section=xs_wg)
    sb_bot_in.rotate(180)
    sb_bot_in.connect("o1", bend_right.ports["o1"])
    
    # 2. Arm Structure (Bottom)
    arm_bot = c << arm_structure()
    arm_bot.rotate(180)
    arm_bot.connect("o1", sb_bot_in.ports["o2"])
    
    # 3. S-Bend Out (Left Side): Inner -> Outer
    # From Y=-0.5 back to Y=-R. Shift = -0.85 = dy.
    sb_bot_out = c << gf.components.bend_s(size=(len_sbend, dy), cross_section=xs_wg)
    sb_bot_out.rotate(180)
    sb_bot_out.connect("o1", arm_bot.ports["o2"])
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = mzi_racetrack_resonator()
    device.show() 
    device.write_gds("mzi_racetrack.gds")