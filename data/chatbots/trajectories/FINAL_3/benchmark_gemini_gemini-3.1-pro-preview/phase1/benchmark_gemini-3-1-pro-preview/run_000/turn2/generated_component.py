import gdsfactory as gf

@gf.cell
def directional_coupler_device():
    """
    Symmetric directional coupler strictly constrained to a [120, 4] um footprint.
    Proportions adjusted to match the thicker waveguides, narrower gap, 
    and extended coupling region seen in the target render.
    """
    c = gf.Component("directional_coupler")

    # --- Adjusted Design Parameters ---
    wg_width = 0.8      # Increased width for a 'chunkier' appearance
    gap = 0.2           # Narrower gap relative to the waveguide width
    
    # Strict footprint bounds
    total_length = 120.0
    total_height = 4.0
    
    # Adjusted segment lengths (must sum to total_length)
    coupling_length = 60.0       # Extended central coupling region (50% of total)
    end_straight_length = 15.0   # Distinct straight ends
    
    # --- Derived Parameters ---
    # Bounding box calculation to strictly hit 4.0um total height
    port_pitch = total_height - wg_width
    
    # Remaining length gets split between the two S-bends
    sbend_length = (total_length - coupling_length - 2 * end_straight_length) / 2
    
    # Calculate vertical shift (dy) required for the S-bends 
    coupling_y = (gap + wg_width) / 2
    dy = (port_pitch / 2) - coupling_y

    # --- Component Primitives ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    straight_end = gf.components.straight(length=end_straight_length, cross_section=xs)
    straight_couple = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # S-bends moving inwards/outwards by the exact required vertical shift
    sbend_up = gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    sbend_down = gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)

    # ==========================
    # --- Assemble Top Arm ---
    # ==========================
    
    tl_straight = c << straight_end
    tl_straight.movey(port_pitch / 2)

    tl_sbend = c << sbend_down
    tl_sbend.connect("o1", tl_straight.ports["o2"])

    t_couple = c << straight_couple
    t_couple.connect("o1", tl_sbend.ports["o2"])

    tr_sbend = c << sbend_up
    tr_sbend.connect("o1", t_couple.ports["o2"])

    tr_straight = c << straight_end
    tr_straight.connect("o1", tr_sbend.ports["o2"])

    # ==========================
    # --- Assemble Bottom Arm ---
    # ==========================
    
    bl_straight = c << straight_end
    bl_straight.movey(-port_pitch / 2)

    bl_sbend = c << sbend_up
    bl_sbend.connect("o1", bl_straight.ports["o2"])

    b_couple = c << straight_couple
    b_couple.connect("o1", bl_sbend.ports["o2"])

    br_sbend = c << sbend_down
    br_sbend.connect("o1", b_couple.ports["o2"])

    br_straight = c << straight_end
    br_straight.connect("o1", br_sbend.ports["o2"])

    # ==========================
    # --- Expose External Ports ---
    # ==========================
    
    c.add_port("o1", port=bl_straight.ports["o1"]) 
    c.add_port("o2", port=tl_straight.ports["o1"]) 
    c.add_port("o3", port=br_straight.ports["o2"]) 
    c.add_port("o4", port=tr_straight.ports["o2"]) 

    return c

if __name__ == "__main__":
    device = directional_coupler_device()
    # Saves strictly to file 
    device.write_gds("directional_coupler.gds")