import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Directional coupler matching the target topology and [120, 4] footprint.
    Constructed using straight port extensions, S-bends, and a central coupler.
    """
    c = gf.Component()

    # --- Dimensions & Constraints ---
    length_total = 120.0
    height_total = 4.0
    
    wg_width = 0.5
    
    # Adjusted parameters to match visual reference
    # Gap increased slightly to match the whitespace ratio in the image relative to waveguide width
    gap = 0.3 
    
    # Longitudinal Partitioning
    # Shortened straight IO to 6um to allow for smoother, longer bends
    l_straight_io = 6.0
    l_coupler = 50.0
    l_bend = (length_total - l_coupler - 2 * l_straight_io) / 2  # 29.0 um

    # Vertical Geometry
    # Ports are centered within the 4um height
    # y_port = +/- (Height - Width)/2
    y_port_offset = (height_total - wg_width) / 2  # 1.75 um
    
    # Coupler waveguides are centered around y=0
    # y_coupler = +/- (Gap + Width)/2
    y_coupler_offset = (gap + wg_width) / 2        # 0.4 um
    
    # Vertical offset for the S-bends
    dy = y_port_offset - y_coupler_offset          # 1.35 um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- 1. Central Coupling Region ---
    # Center the coupler at x=0
    coupler = c << gf.components.coupler_straight(
        length=l_coupler,
        gap=gap,
        cross_section=xs
    )
    coupler.movex(-l_coupler / 2)

    # --- 2. Define Building Blocks ---
    # S-Bend: Transitions vertically by 'dy' over length 'l_bend'
    # bend_s creates a cosine/sine bend by default which matches the target's smoothness
    bend_ref = gf.components.bend_s(
        size=(l_bend, dy),
        cross_section=xs
    )
    # Straight: Port extension
    straight_ref = gf.components.straight(
        length=l_straight_io,
        cross_section=xs
    )

    # --- 3. Assemble Arms ---

    # -- Left Side (Inputs) --
    
    # Bottom-Left Arm (Connects to Port o1 of coupler)
    # Sequence: Straight -> Bend(Up) -> Coupler
    lb_bend = c << bend_ref
    lb_bend.connect("o2", coupler.ports["o1"]) 
    
    lb_straight = c << straight_ref
    lb_straight.connect("o2", lb_bend.ports["o1"])

    # Top-Left Arm (Connects to Port o2 of coupler)
    # Sequence: Straight -> Bend(Down) -> Coupler
    # We mirror the S-bend to create the downward transition
    lt_bend = c << bend_ref
    lt_bend.mirror_y()
    lt_bend.connect("o2", coupler.ports["o2"])
    
    lt_straight = c << straight_ref
    lt_straight.connect("o2", lt_bend.ports["o1"])

    # -- Right Side (Outputs) --

    # Top-Right Arm (Connects to Port o3 of coupler)
    # Sequence: Coupler -> Bend(Up) -> Straight
    rt_bend = c << bend_ref
    rt_bend.connect("o1", coupler.ports["o3"])
    
    rt_straight = c << straight_ref
    rt_straight.connect("o1", rt_bend.ports["o2"])

    # Bottom-Right Arm (Connects to Port o4 of coupler)
    # Sequence: Coupler -> Bend(Down) -> Straight
    rb_bend = c << bend_ref
    rb_bend.mirror_y()
    rb_bend.connect("o1", coupler.ports["o4"])
    
    rb_straight = c << straight_ref
    rb_straight.connect("o1", rb_bend.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=lb_straight.ports["o1"])
    c.add_port("o2", port=lt_straight.ports["o1"])
    c.add_port("o3", port=rt_straight.ports["o2"])
    c.add_port("o4", port=rb_straight.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_refined()
    device.show()
    device.write_gds("directional_coupler_refined.gds")