import gdsfactory as gf

@gf.cell
def heater_straight_section(length=1.4, width=0.5, hole_size=(0.4, 0.2)):
    """
    Creates a straight waveguide section with two rectangular 'holes' 
    subtracted from it to mimic the heater pads.
    """
    # 1. Create the main body (Waveguide)
    c_body = gf.Component()
    c_body << gf.components.rectangle(size=(length, width), layer=(1, 0), centered=True)

    # 2. Create the holes (Mask)
    c_holes = gf.Component()
    h_len, h_width = hole_size
    gap = 0.15
    shift = (gap + h_len) / 2
    
    # Left Hole
    h1 = c_holes << gf.components.rectangle(size=(h_len, h_width), layer=(1, 0), centered=True)
    h1.movex(-shift)
    
    # Right Hole
    h2 = c_holes << gf.components.rectangle(size=(h_len, h_width), layer=(1, 0), centered=True)
    h2.movex(shift)

    # 3. Perform Boolean: Body - Holes
    # This generates a new component with the geometry subtracted
    c_final = gf.boolean(c_body, c_holes, operation="not", layer=(1, 0))
    
    # 4. Create wrapper component to add ports correctly
    c = gf.Component()
    # Add the boolean result geometry
    c << c_final
    
    # Add ports manually (since boolean destroys original ports)
    c.add_port("o1", center=(-length/2, 0), width=width, orientation=180, layer=(1, 0))
    c.add_port("o2", center=(length/2, 0), width=width, orientation=0, layer=(1, 0))
    
    return c

@gf.cell
def racetrack_mzi_modulator():
    """
    Recreates the pinched racetrack resonator.
    - Footprint: ~3.0um x 5.5um
    - Features: Thick black waveguide with white 'pad' cutouts in the straight sections.
    """
    c = gf.Component()

    # --- 1. Dimensions ---
    wg_width = 0.5 
    
    # Geometry Constraints
    # Total Height = 3.0 -> Radius = 1.25
    r_outer = 1.25
    
    # Inner Pinch gap
    inner_gap = 0.4
    y_straight_offset = (inner_gap + wg_width) / 2  # 0.45
    
    # S-bend vertical transition
    dy_sbend = r_outer - y_straight_offset # 1.25 - 0.45 = 0.8
    
    # Horizontal constraints
    # Total Width 5.5 = 2.5 (2*R) + 2*0.8 (S-bends) + 1.4 (Straight)
    sbend_x = 0.8
    straight_len = 1.4 
    
    # Define Cross Section
    # radius_min=0.01 is required to allow tight S-bends without errors
    xs = gf.cross_section.cross_section(
        width=wg_width,
        layer=(1, 0),
        radius=r_outer,
        radius_min=0.01 
    )

    # --- 2. Sequential Construction (Counter-Clockwise) ---
    
    # A. Bottom Straight Section
    bot_str = c << heater_straight_section(length=straight_len, width=wg_width)
    bot_str.move((0, -y_straight_offset))
    
    # B. Bottom Right S-Bend (Goes Down/Out)
    # Connects to Right port (o2) of bottom straight
    # Transition: y=-0.45 -> y=-1.25 (dy = -0.8)
    s_bot_right = c << gf.components.bend_s(
        size=(sbend_x, -dy_sbend), 
        cross_section=xs
    )
    s_bot_right.connect("o1", bot_str.ports["o2"])
    
    # C. Right Bend (180 deg)
    # Connects to S-bend. Turns North then West.
    r_bend = c << gf.components.bend_euler(radius=r_outer, angle=180, p=0.5, cross_section=xs)
    r_bend.connect("o1", s_bot_right.ports["o2"])
    
    # D. Top Right S-Bend (Goes Down/In)
    # Connects to Top of Right Bend (facing West).
    # Transition: y=1.25 -> y=0.45
    # Since facing West, Local +dy corresponds to Global -dy (Down).
    s_top_right = c << gf.components.bend_s(
        size=(sbend_x, dy_sbend), 
        cross_section=xs
    )
    s_top_right.connect("o1", r_bend.ports["o2"])
    
    # E. Top Straight Section
    top_str = c << heater_straight_section(length=straight_len, width=wg_width)
    # Connect o2 (Right side) to S-bend (on the right)
    top_str.connect("o2", s_top_right.ports["o2"]) 
    
    # F. Top Left S-Bend (Goes Up/Out)
    # Connects to Left port (o1) of top straight.
    # Transition: y=0.45 -> y=1.25
    # Facing West -> Local -dy corresponds to Global +dy (Up).
    s_top_left = c << gf.components.bend_s(
        size=(sbend_x, -dy_sbend), 
        cross_section=xs
    )
    s_top_left.connect("o1", top_str.ports["o1"])
    
    # G. Left Bend (180 deg)
    # Connects to S-bend. Turns South then East.
    l_bend = c << gf.components.bend_euler(radius=r_outer, angle=180, p=0.5, cross_section=xs)
    l_bend.connect("o1", s_top_left.ports["o2"])
    
    # H. Bottom Left S-Bend (Goes Down/In)
    # Connects to Bottom of Left Bend (facing East).
    # Transition: y=-1.25 -> y=-0.45
    # Facing East -> Local +dy corresponds to Global +dy (Up).
    s_bot_left = c << gf.components.bend_s(
        size=(sbend_x, dy_sbend), 
        cross_section=xs
    )
    s_bot_left.connect("o1", l_bend.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = racetrack_mzi_modulator()
    device.show()
    device.write_gds("racetrack_mzi.gds")