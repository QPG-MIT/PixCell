import gdsfactory as gf

@gf.cell
def recreated_device():
    c = gf.Component("Parametric_Device_Recreation_Refined")

    # ==========================================
    # 1. Define Parameters (Finer Features)
    # ==========================================
    # Constraints
    length_total = 120.0
    max_height = 4.0  # The device must fit within Y = +/- 2.0
    
    # Inner Waveguide Bundle
    # The original image shows fine lines. 
    wg_width = 0.18
    wg_gap = 0.18
    num_central_wgs = 5
    
    # Outer "Rail" Structures
    # In the target, these are thicker than the inner WGs, but not massive blocks.
    outer_rail_width = 0.6
    gap_bundle_to_rail = 0.25  # Gap between the bundle and the straight part of the rail
    
    # Lengths
    bend_length = 20.0  # Longer bend for a smoother look
    straight_length = length_total - 2 * bend_length

    # ==========================================
    # 2. Define Cross Sections
    # ==========================================
    xs_center = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    xs_outer = gf.cross_section.cross_section(width=outer_rail_width, layer=(1, 0))

    # ==========================================
    # 3. Build Central Bundle (5 Straights)
    # ==========================================
    # Calculate pitch and offsets to center the bundle at Y=0
    pitch = wg_width + wg_gap
    y_offsets = [pitch * (i - (num_central_wgs - 1) / 2) for i in range(num_central_wgs)]
    
    # Calculate the Y-coordinate of the top edge of the bundle for later reference
    # Top WG center is the last element of y_offsets
    top_wg_center = y_offsets[-1]
    bundle_top_edge = top_wg_center + wg_width / 2
    
    for y in y_offsets:
        wg = c << gf.components.straight(length=length_total, cross_section=xs_center)
        wg.y = y

    # ==========================================
    # 4. Build Outer Flared Rails
    # ==========================================
    # Logic: The rail is straight in the middle and bends OUTWARDS at the ends.
    
    # --- Vertical Position Calculations ---
    # Inner edge of the rail in the straight section
    rail_inner_y_straight = bundle_top_edge + gap_bundle_to_rail
    # Center Y of the rail in the straight section
    rail_center_y_straight = rail_inner_y_straight + outer_rail_width / 2
    
    # Determine Flare Height
    # We want the outer edge of the rail at the PORT (end) to be at Y = max_height / 2
    # Top edge limit = 2.0
    # Center Y at port = 2.0 - outer_rail_width / 2
    rail_center_y_port = (max_height / 2) - (outer_rail_width / 2)
    
    # The vertical shift (dy) for the S-bend
    # From straight (center) to port (outer), we move UP
    flare_dy = rail_center_y_port - rail_center_y_straight

    # --- Create Primitives ---
    # Straight Section
    outer_straight = gf.components.straight(
        length=straight_length, 
        cross_section=xs_outer
    )
    
    # Left Bend (Input): Goes from Port (High Y) down to Straight (Low Y)
    # Using bend_s with negative Y size implies dropping down
    bend_in_down = gf.components.bend_s(
        size=(bend_length, -flare_dy), 
        cross_section=xs_outer
    )
    # Inverted version for the bottom (Goes from Low Y up to Straight)
    bend_in_up = gf.components.bend_s(
        size=(bend_length, flare_dy), 
        cross_section=xs_outer
    )

    # Right Bend (Output): Goes from Straight (Low Y) up to Port (High Y)
    bend_out_up = gf.components.bend_s(
        size=(bend_length, flare_dy), 
        cross_section=xs_outer
    )
    # Inverted version for the bottom
    bend_out_down = gf.components.bend_s(
        size=(bend_length, -flare_dy), 
        cross_section=xs_outer
    )

    # --- Assembly: TOP RAIL ---
    # Place Straight
    ref_top_str = c << outer_straight
    ref_top_str.x = length_total / 2
    ref_top_str.y = rail_center_y_straight
    
    # Connect Input Bend (Left)
    # Connect o2 of bend (end) to o1 of straight (start)
    ref_top_in = c << bend_in_down
    ref_top_in.connect("o2", ref_top_str.ports["o1"])
    
    # Connect Output Bend (Right)
    # Connect o1 of bend (start) to o2 of straight (end)
    ref_top_out = c << bend_out_up
    ref_top_out.connect("o1", ref_top_str.ports["o2"])

    # --- Assembly: BOTTOM RAIL (Mirrored) ---
    ref_bot_str = c << outer_straight
    ref_bot_str.x = length_total / 2
    ref_bot_str.y = -rail_center_y_straight
    
    # Connect Input Bend (Left) - coming UP from bottom port
    ref_bot_in = c << bend_in_up
    ref_bot_in.connect("o2", ref_bot_str.ports["o1"])
    
    # Connect Output Bend (Right) - going DOWN to bottom port
    ref_bot_out = c << bend_out_down
    ref_bot_out.connect("o1", ref_bot_str.ports["o2"])

    return c

if __name__ == "__main__":
    device = recreated_device()
    device.show()
    device.write_gds("recreated_device_refined.gds")