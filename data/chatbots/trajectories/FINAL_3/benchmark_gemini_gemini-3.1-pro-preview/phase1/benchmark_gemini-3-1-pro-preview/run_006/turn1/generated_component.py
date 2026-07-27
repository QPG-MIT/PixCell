import gdsfactory as gf

@gf.cell
def symmetric_directional_coupler(
    total_length: float = 120.0,
    port_pitch: float = 4.0,
    gap: float = 0.2,
    wg_width: float = 0.5,
    straight_ratio: float = 0.5
) -> gf.Component:
    """
    Creates a symmetric directional coupler matching the [120, 4] footprint constraint.
    
    Args:
        total_length: Total X-axis length of the device (constrained to 120 um).
        port_pitch: Y-axis distance between the outer ports (constrained to 4 um).
        gap: Distance between the waveguides in the straight coupling region.
        wg_width: Waveguide width.
        straight_ratio: Ratio of the total length occupied by the central straight section.
    """
    c = gf.Component("directional_coupler")
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Geometry Calculations ---
    # Length of the middle straight sections
    straight_l = total_length * straight_ratio
    # X-span available for each S-bend
    sbend_x = (total_length - straight_l) / 2.0

    # Center-to-center pitch of waveguides in the coupling region
    pitch_mid = wg_width + gap
    # Y-shift required for the S-bends to transition from outer pitch to inner gap
    sbend_y = (port_pitch - pitch_mid) / 2.0

    # --- Create Parametric Primitives ---
    straight_top = gf.components.straight(length=straight_l, cross_section=xs)
    straight_bot = gf.components.straight(length=straight_l, cross_section=xs)

    # Input S-bends (Left side)
    # Top input shifts DOWN (-Y) to meet the coupling region
    bend_top_in = gf.components.bend_s(size=(sbend_x, -sbend_y), cross_section=xs)
    # Bottom input shifts UP (+Y) to meet the coupling region
    bend_bot_in = gf.components.bend_s(size=(sbend_x, sbend_y), cross_section=xs)

    # Output S-bends (Right side)
    # Top output shifts UP (+Y) to diverge from the coupling region
    bend_top_out = gf.components.bend_s(size=(sbend_x, sbend_y), cross_section=xs)
    # Bottom output shifts DOWN (-Y) to diverge from the coupling region
    bend_bot_out = gf.components.bend_s(size=(sbend_x, -sbend_y), cross_section=xs)

    # --- Assembly Pattern (Adding References) ---
    st_top_ref = c << straight_top
    st_bot_ref = c << straight_bot

    b_top_in_ref = c << bend_top_in
    b_bot_in_ref = c << bend_bot_in
    b_top_out_ref = c << bend_top_out
    b_bot_out_ref = c << bend_bot_out

    # --- Position and Connect ---
    # 1. Place the central coupling sections symmetrically across the Y-axis
    st_top_ref.move((0, pitch_mid / 2.0))
    st_bot_ref.move((0, -pitch_mid / 2.0))

    # 2. Connect input S-bends to the left side of the straight sections
    # Connects port 'o2' (right side) of the bends to port 'o1' (left side) of straights
    b_top_in_ref.connect("o2", st_top_ref.ports["o1"])
    b_bot_in_ref.connect("o2", st_bot_ref.ports["o1"])

    # 3. Connect output S-bends to the right side of the straight sections
    # Connects port 'o1' (left side) of the bends to port 'o2' (right side) of straights
    b_top_out_ref.connect("o1", st_top_ref.ports["o2"])
    b_bot_out_ref.connect("o1", st_bot_ref.ports["o2"])

    # --- Expose External Ports ---
    # Following standard naming: Left ports are o1/o2, Right ports are o3/o4
    c.add_port("o1", port=b_bot_in_ref.ports["o1"])   # Bottom-Left
    c.add_port("o2", port=b_top_in_ref.ports["o1"])   # Top-Left
    c.add_port("o3", port=b_bot_out_ref.ports["o2"])  # Bottom-Right
    c.add_port("o4", port=b_top_out_ref.ports["o2"])  # Top-Right

    return c

if __name__ == "__main__":
    # Generate the device with the exact requested footprint (120um x 4um pitch)
    device = symmetric_directional_coupler()
    
    # Save the GDS to disk
    device.write_gds("directional_coupler_120x4.gds")