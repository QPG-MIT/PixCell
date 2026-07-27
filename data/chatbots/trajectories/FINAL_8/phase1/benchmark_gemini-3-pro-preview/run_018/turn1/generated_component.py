import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreation of the device based on the image and catalog.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component("Parametric_Coupler_Recreation")

    # ---------------------------------------------------------
    # Parameters derived from Visual Analysis & Constraints
    # ---------------------------------------------------------
    total_length = 120.0
    
    # Waveguide dimensions (estimated for fine stripes)
    line_width = 0.15
    line_gap = 0.15
    line_pitch = line_width + line_gap
    
    # Layer definition (Standard waveguide layer)
    wg_layer = (1, 0)
    
    # Create the standard cross-section
    xs = gf.cross_section.cross_section(width=line_width, layer=wg_layer)

    # ---------------------------------------------------------
    # 1. Center Bundle (5 Straight Waveguides)
    # ---------------------------------------------------------
    # The center is straight, length 120um.
    # We place 5 lines centered around y=0.
    
    num_center_lines = 5
    center_y_start = -((num_center_lines - 1) * line_pitch) / 2
    
    for i in range(num_center_lines):
        y_pos = center_y_start + (i * line_pitch)
        
        # Create straight segment
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.movey(y_pos)

    # ---------------------------------------------------------
    # 2. Top Wing (4 Curved Waveguides)
    # ---------------------------------------------------------
    # The wing needs to dip down and go back up.
    # We construct this using two bend_s components back-to-back.
    # Dimensions: Total L=120, so each bend is L=60.
    
    num_wing_lines = 4
    wing_vertical_drop = 0.8  # Amount the wing bends towards center
    
    # Gap between center bundle and closest wing line at the "waist" (middle)
    # Visual estimate: small gap, approx 0.2um
    coupling_gap = 0.2
    
    # Calculate where the bottom-most line of the top wing sits at the edges
    # Top of center bundle is at: abs(center_y_start)
    center_top_edge = abs(center_y_start)
    
    # At the waist (middle), y = center_top_edge + coupling_gap
    # At the edges (left/right), y = waist_y + wing_vertical_drop
    waist_y_base = center_top_edge + coupling_gap + (line_width/2)
    
    for i in range(num_wing_lines):
        # Calculate Y offset for this specific stripe in the wing bundle
        stripe_offset = i * line_pitch
        
        # Start Y position (at left edge)
        # It starts high, goes down by 'wing_vertical_drop', then goes up.
        start_y = waist_y_base + stripe_offset + wing_vertical_drop
        
        # Part A: S-Bend Down (Left Half)
        # Connects (0, y_start) to (60, y_waist)
        # size tuple is (length_x, height_change_y)
        bend_down = c << gf.components.bend_s(
            size=(total_length / 2, -wing_vertical_drop), 
            cross_section=xs
        )
        bend_down.move((0, start_y))
        
        # Part B: S-Bend Up (Right Half)
        # Connects from the end of Part A back up
        bend_up = c << gf.components.bend_s(
            size=(total_length / 2, wing_vertical_drop), 
            cross_section=xs
        )
        # Connect Part B to Part A
        bend_up.connect("o1", bend_down.ports["o2"])

    # ---------------------------------------------------------
    # 3. Bottom Wing (Mirror of Top Wing)
    # ---------------------------------------------------------
    # We repeat the logic for the bottom, mirroring the Y coordinates.
    
    for i in range(num_wing_lines):
        stripe_offset = i * line_pitch
        
        # Mirror coordinates:
        # Waist is at negative Y.
        # Vertical drop means going UP towards the edge (away from center).
        
        neg_waist_y_base = -(center_top_edge + coupling_gap + (line_width/2))
        start_y = neg_waist_y_base - stripe_offset - wing_vertical_drop
        
        # Part A: S-Bend Up (Left Half) - moves from low to high (towards center)
        bend_in = c << gf.components.bend_s(
            size=(total_length / 2, wing_vertical_drop), 
            cross_section=xs
        )
        bend_in.move((0, start_y))
        
        # Part B: S-Bend Down (Right Half) - moves from high to low (away from center)
        bend_out = c << gf.components.bend_s(
            size=(total_length / 2, -wing_vertical_drop), 
            cross_section=xs
        )
        bend_out.connect("o1", bend_in.ports["o2"])

    return c

# ---------------------------------------------------------
# Generate and Save
# ---------------------------------------------------------
if __name__ == "__main__":
    device = recreate_device()
    device.show() # View in KLayout
    device.write_gds("parametric_device.gds")