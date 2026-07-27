import gdsfactory as gf

@gf.cell
def directional_coupler_device():
    """
    Symmetric directional coupler strictly constrained to a [120, 4] um footprint.
    Constructed purely from parametric primitives (straights and S-bends).
    """
    c = gf.Component("directional_coupler")

    # Define the cross-section
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Strict footprint parameters
    total_length = 120.0
    total_height = 4.0
    
    # Internal coupling design parameters
    gap = 0.2
    coupling_length = 40.0
    end_straight_length = 10.0

    # --- Derived Parameters ---
    # To make the bounding box exactly 4.0um tall, port pitch + wg_width must equal 4.0
    port_pitch = total_height - wg_width
    
    # Calculate available length for S-bends to hit exactly 120um total
    sbend_length = (total_length - coupling_length - 2 * end_straight_length) / 2
    
    # Calculate vertical shift required for the S-bends 
    # Starts at port_pitch/2, ends at coupling gap (gap/2 + width/2)
    coupling_y = (gap + wg_width) / 2
    dy = (port_pitch / 2) - coupling_y

    # --- Component Primitives ---
    straight_end = gf.components.straight(length=end_straight_length, cross_section=xs)
    straight_couple = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # S-bend moving 'up' and 'down' by the required delta-Y
    sbend_up = gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    sbend_down = gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)

    # ==========================
    # --- Assemble Top Arm ---
    # ==========================
    
    # 1. Top input straight
    tl_straight = c << straight_end
    tl_straight.movey(port_pitch / 2)

    # 2. S-bend tapering inwards (down)
    tl_sbend = c << sbend_down
    tl_sbend.connect("o1", tl_straight.ports["o2"])

    # 3. Parallel coupling region
    t_couple = c << straight_couple
    t_couple.connect("o1", tl_sbend.ports["o2"])

    # 4. S-bend tapering outwards (up)
    tr_sbend = c << sbend_up
    tr_sbend.connect("o1", t_couple.ports["o2"])

    # 5. Top output straight
    tr_straight = c << straight_end
    tr_straight.connect("o1", tr_sbend.ports["o2"])

    # ==========================
    # --- Assemble Bottom Arm ---
    # ==========================
    
    # 1. Bottom input straight
    bl_straight = c << straight_end
    bl_straight.movey(-port_pitch / 2)

    # 2. S-bend tapering inwards (up)
    bl_sbend = c << sbend_up
    bl_sbend.connect("o1", bl_straight.ports["o2"])

    # 3. Parallel coupling region
    b_couple = c << straight_couple
    b_couple.connect("o1", bl_sbend.ports["o2"])

    # 4. S-bend tapering outwards (down)
    br_sbend = c << sbend_down
    br_sbend.connect("o1", b_couple.ports["o2"])

    # 5. Bottom output straight
    br_straight = c << straight_end
    br_straight.connect("o1", br_sbend.ports["o2"])

    # ==========================
    # --- Expose External Ports ---
    # ==========================
    
    # Following standard left-to-right, bottom-to-top numbering
    c.add_port("o1", port=bl_straight.ports["o1"]) # Bottom-Left
    c.add_port("o2", port=tl_straight.ports["o1"]) # Top-Left
    c.add_port("o3", port=br_straight.ports["o2"]) # Bottom-Right
    c.add_port("o4", port=tr_straight.ports["o2"]) # Top-Right

    return c

if __name__ == "__main__":
    # Instantiate the cell and write it to a GDS file
    device = directional_coupler_device()
    device.write_gds("directional_coupler.gds")