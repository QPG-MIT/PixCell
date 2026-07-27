import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler with a 120um x 4um footprint.
    Parameters are refined based on the target image:
    - Waveguide width set to 0.7um to match the visual 'weight' of the lines.
    - Gap maintained at 0.2um.
    - Segmentation tuned: Input straights are longer (20um), S-bends are shorter/steeper (15um), 
      and coupling region remains 50um. This matches the distinct straight lead-ins and 
      steeper transition curves seen in the reference.
    """
    c = gf.Component()

    # --- Design Parameters ---
    length_total = 120.0
    height_total = 4.0
    
    wg_width = 0.7
    wg_gap = 0.2
    
    # Segment lengths calculated from pixel ratio analysis of the target image
    length_couple = 50.0  
    length_bend = 15.0    # Shortened for sharper transition
    length_io = (length_total - length_couple - 2 * length_bend) / 2  # (120 - 50 - 30)/2 = 20.0
    
    # Vertical Offsets
    # Inner region: centered around y=0 with gap
    y_couple_offset = (wg_gap + wg_width) / 2
    
    # Outer region: aligned to the 4um footprint boundary
    # Top edge = +2.0, so center = 2.0 - width/2
    y_port_offset = (height_total / 2) - (wg_width / 2)
    
    # Bend vertical displacement
    dy = y_port_offset - y_couple_offset
    
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- Top Arm ---
    # 1. Input Straight (Left)
    t_in = c << gf.components.straight(length=length_io, cross_section=xs)
    t_in.move((-length_total/2, y_port_offset))
    
    # 2. S-Bend (Down to coupling region)
    t_bend_in = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    t_bend_in.connect("o1", t_in.ports["o2"])
    
    # 3. Coupling Straight (Middle)
    t_mid = c << gf.components.straight(length=length_couple, cross_section=xs)
    t_mid.connect("o1", t_bend_in.ports["o2"])
    
    # 4. S-Bend (Up to output port)
    t_bend_out = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    t_bend_out.connect("o1", t_mid.ports["o2"])
    
    # 5. Output Straight (Right)
    t_out = c << gf.components.straight(length=length_io, cross_section=xs)
    t_out.connect("o1", t_bend_out.ports["o2"])

    # --- Bottom Arm ---
    # 1. Input Straight (Left)
    b_in = c << gf.components.straight(length=length_io, cross_section=xs)
    b_in.move((-length_total/2, -y_port_offset))
    
    # 2. S-Bend (Up to coupling region)
    b_bend_in = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    b_bend_in.connect("o1", b_in.ports["o2"])
    
    # 3. Coupling Straight (Middle)
    b_mid = c << gf.components.straight(length=length_couple, cross_section=xs)
    b_mid.connect("o1", b_bend_in.ports["o2"])
    
    # 4. S-Bend (Down to output port)
    b_bend_out = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    b_bend_out.connect("o1", b_mid.ports["o2"])
    
    # 5. Output Straight (Right)
    b_out = c << gf.components.straight(length=length_io, cross_section=xs)
    b_out.connect("o1", b_bend_out.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=b_in.ports["o1"])
    c.add_port("o2", port=t_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_120x4()
    device.write_gds("directional_coupler_120x4.gds")
    device.show()