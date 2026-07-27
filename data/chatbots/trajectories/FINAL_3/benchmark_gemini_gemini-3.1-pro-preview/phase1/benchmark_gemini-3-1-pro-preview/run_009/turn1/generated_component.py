import gdsfactory as gf

@gf.cell
def directional_coupler():
    c = gf.Component()
    
    # Define standard cross section
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Footprint & Geometry Constraints ---
    total_length = 120.0
    total_height = 4.0
    gap = 0.2

    # Y-coordinates calculations
    # Port centers placed to perfectly bound a 4.0um height with 0.5um waveguides
    port_y = (total_height - wg_width) / 2.0  # 1.75
    # Coupling region centers
    couple_y = (gap + wg_width) / 2.0         # 0.35
    # S-bend vertical displacement
    sbend_dy = port_y - couple_y              # 1.4

    # X-coordinates / lengths distribution (Total = 120)
    Lx = 15.0       # Input/Output straight length
    S_dx = 25.0     # S-bend horizontal length
    Lc = total_length - (2 * Lx) - (2 * S_dx) # Central coupling length = 40.0

    # --- Base Primitives ---
    str_inout = gf.components.straight(length=Lx, cross_section=xs)
    str_couple = gf.components.straight(length=Lc, cross_section=xs)
    
    # S-bends going up and down
    sbend_down = gf.components.bend_s(size=(S_dx, -sbend_dy), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(S_dx, sbend_dy), cross_section=xs)

    # --- Assemble Top Arm ---
    t_in = c << str_inout
    t_in.move((0, port_y))

    t_sb1 = c << sbend_down
    t_sb1.connect("o1", t_in.ports["o2"])

    t_c = c << str_couple
    t_c.connect("o1", t_sb1.ports["o2"])

    t_sb2 = c << sbend_up
    t_sb2.connect("o1", t_c.ports["o2"])

    t_out = c << str_inout
    t_out.connect("o1", t_sb2.ports["o2"])

    # --- Assemble Bottom Arm ---
    b_in = c << str_inout
    b_in.move((0, -port_y))

    b_sb1 = c << sbend_up
    b_sb1.connect("o1", b_in.ports["o2"])

    b_c = c << str_couple
    b_c.connect("o1", b_sb1.ports["o2"])

    b_sb2 = c << sbend_down
    b_sb2.connect("o1", b_c.ports["o2"])

    b_out = c << str_inout
    b_out.connect("o1", b_sb2.ports["o2"])

    # --- Expose External Ports ---
    c.add_port("o1", port=t_in.ports["o1"])  # Top left
    c.add_port("o2", port=b_in.ports["o1"])  # Bottom left
    c.add_port("o3", port=t_out.ports["o2"]) # Top right
    c.add_port("o4", port=b_out.ports["o2"]) # Bottom right

    return c

if __name__ == "__main__":
    # Create the component and save it to a GDS file
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")