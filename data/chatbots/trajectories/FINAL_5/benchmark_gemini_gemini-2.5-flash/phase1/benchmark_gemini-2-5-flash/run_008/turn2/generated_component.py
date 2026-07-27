import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

@gf.cell
def create_single_arm(
    y_outer_center: float,
    dy_vertical_shift: float,
    xs_outer: CrossSectionSpec,
    xs_inner: CrossSectionSpec,
    l_outer_straight: float,
    l_bars_section: float,
    l_transition_x: float, # Horizontal extent of the s-bend transition
    r_end_cap: float,
    bar_width: float,
    bar_pitch: float,
    n_bars: int,
    bar_height_slot: float,
    layer: tuple = (1, 0),
    mirror_y: bool = False # For bottom arm, reverses vertical components
) -> gf.Component:
    arm_c = gf.Component()
    
    # Define transitions for varying width extrusions
    trans_wide_to_narrow = gf.path.transition(xs_outer, xs_inner, width_type='sine')
    trans_narrow_to_wide = gf.path.transition(xs_inner, xs_outer, width_type='sine')

    # Component to collect all solid parts of the arm before slot subtraction
    arm_body_parts = gf.Component("arm_body_parts") 

    # --- 1. Left End Cap (Semicircle) ---
    # Create a full circle centered at (0,0) by default, then move it
    circle_left = gf.components.circle(radius=r_end_cap, layer=layer)
    circle_left.movey(y_outer_center)
    # Create a rectangle to cut the circle, leaving the left half
    rect_left_cut = gf.components.rectangle(size=(r_end_cap, 2 * r_end_cap), layer=layer, centered=True)
    rect_left_cut.movex(-r_end_cap/2) # Position to cut the right half of circle
    rect_left_cut.movey(y_outer_center)
    
    # Perform boolean AND to get the left semicircle
    end_cap_left_comp_result = gf.boolean(circle_left, rect_left_cut, operation="and", layer=layer)
    
    # FIX: Add the port to the boolean result component *before* it is added as a reference
    end_cap_left_comp_result.add_port("o2", center=(end_cap_left_comp_result.xmax, y_outer_center), width=xs_outer.width, orientation=0, layer=layer)
    
    end_cap_left_ref = arm_body_parts << end_cap_left_comp_result


    # --- 2. Left Outer Straight Section ---
    c_outer_left = arm_body_parts << gf.components.straight(length=l_outer_straight, cross_section=xs_outer)
    c_outer_left.connect("o1", end_cap_left_ref.ports["o2"])

    # --- 3. Transition In (Wide to Narrow, Curved) ---
    # Create a dummy bend_s to get the path for the S-curve
    bend_s_dummy_in = gf.components.bend_s(
        size=(l_transition_x, dy_vertical_shift if not mirror_y else -dy_vertical_shift),
        cross_section=gf.cross_section.cross_section(width=0.1, layer=layer) # Dummy cross-section
    )
    p_trans_in = bend_s_dummy_in.get_paths()[0] # Extract the Path object

    # Extrude the path with the width transition function
    c_trans_in = arm_body_parts << gf.path.extrude_transition(p_trans_in, transition=trans_wide_to_narrow)
    c_trans_in.connect("o1", c_outer_left.ports["o2"])

    # --- 4. Inner Narrow Straight Section (body where slots are) ---
    c_inner_straight = arm_body_parts << gf.components.straight(length=l_bars_section, cross_section=xs_inner)
    c_inner_straight.connect("o1", c_trans_in.ports["o2"])

    # --- Create the comb slots (rectangles to be subtracted) ---
    slots_to_subtract = gf.Component("slots_to_subtract")
    for i in range(n_bars):
        slot_rect = slots_to_subtract << gf.components.rectangle(
            size=(bar_width, bar_height_slot * 2), # Total height of slot
            layer=layer, centered=True
        )
        # Calculate x-center for each slot
        slot_x_center = c_inner_straight.ports["o1"].x + (i * bar_pitch) + bar_width / 2
        
        # Position `ymid` of the slot such that its *inner* edge aligns with the *inner* edge of the arm.
        if not mirror_y: # Top arm: Slots are on the bottom edge of the arm, extending downwards into the gap.
            slot_rect.ymid = c_inner_straight.ymid - xs_inner.width/2 + bar_height_slot 
        else: # Bottom arm: Slots are on the top edge of the arm, extending upwards into the gap.
            slot_rect.ymid = c_inner_straight.ymid + xs_inner.width/2 - bar_height_slot
        
        slot_rect.x = slot_x_center

    # --- 5. Transition Out (Narrow to Wide, Curved) ---
    bend_s_dummy_out = gf.components.bend_s(
        size=(l_transition_x, -dy_vertical_shift if not mirror_y else dy_vertical_shift),
        cross_section=gf.cross_section.cross_section(width=0.1, layer=layer)
    )
    p_trans_out = bend_s_dummy_out.get_paths()[0]

    c_trans_out = arm_body_parts << gf.path.extrude_transition(p_trans_out, transition=trans_narrow_to_wide)
    c_trans_out.connect("o1", c_inner_straight.ports["o2"])

    # --- 6. Right Outer Straight Section ---
    c_outer_right = arm_body_parts << gf.components.straight(length=l_outer_straight, cross_section=xs_outer)
    c_outer_right.connect("o1", c_trans_out.ports["o2"])

    # --- 7. Right End Cap (Semicircle) ---
    circle_right = gf.components.circle(radius=r_end_cap, layer=layer)
    circle_right.movey(y_outer_center)
    rect_right_cut = gf.components.rectangle(size=(r_end_cap, 2 * r_end_cap), layer=layer, centered=True)
    rect_right_cut.movex(r_end_cap/2) # Position to cut the left half of circle
    rect_right_cut.movey(y_outer_center)

    end_cap_right_comp_result = gf.boolean(circle_right, rect_right_cut, operation="and", layer=layer)
    
    # FIX: Add the port to the boolean result component *before* it is added as a reference
    end_cap_right_comp_result.add_port("o1", center=(end_cap_right_comp_result.xmin, y_outer_center), width=xs_outer.width, orientation=180, layer=layer)
    
    end_cap_right_ref = arm_body_parts << end_cap_right_comp_result
    end_cap_right_ref.connect("o1", c_outer_right.ports["o2"])

    # --- Final Boolean Operations ---
    # `arm_body_parts` now contains all the solid parts merged into one polygon
    final_arm_shape = gf.boolean(arm_body_parts, slots_to_subtract, operation="not", layer=layer)
    
    # Add the final, fully processed arm shape to the component being returned
    arm_c << final_arm_shape

    return arm_c

# --- Main Device Function ---
@gf.cell
def device_from_image():
    c = gf.Component("device_from_image_fixed")

    # --- Device Dimensions ---
    X_TOTAL = 18.24
    Y_TOTAL = 0.7
    LAYER = (1, 0)

    W_OUTER_ARM = 0.3
    W_INNER_ARM = 0.1
    G_CENTRAL_GAP = 0.1 # Gap between inner edges of narrow sections

    # --- Derived Y-coordinates ---
    Y_CENTER_LINE = 0.0 # Device is centered horizontally
    Y_OUTER_CENTER_TOP = Y_TOTAL / 2 - W_OUTER_ARM / 2  # 0.35 - 0.15 = 0.2
    Y_INNER_CENTER_TOP = G_CENTRAL_GAP / 2 + W_INNER_ARM / 2 # 0.05 + 0.05 = 0.1
    DY_VERTICAL_SHIFT = Y_OUTER_CENTER_TOP - Y_INNER_CENTER_TOP # 0.1

    Y_OUTER_CENTER_BOTTOM = -Y_OUTER_CENTER_TOP
    Y_INNER_CENTER_BOTTOM = -Y_INNER_CENTER_TOP

    # --- Feature Dimensions ---
    R_END_CAP = W_OUTER_ARM / 2 # Radius for the rounded ends: 0.15

    L_BARS_SECTION = 8.5 # Horizontal length of the comb section
    BAR_WIDTH = 0.1 # Width of each slot (white)
    BAR_GAP = 0.2 # Gap between slots
    BAR_PITCH = BAR_WIDTH + BAR_GAP # Distance from start of one bar to start of next
    N_BARS = 29
    BAR_HEIGHT_SLOT = W_INNER_ARM / 2 # Height of the slots: 0.05 (half the narrow arm width)

    L_TRANSITION_X = 2.0 # Horizontal extent of each curved transition (for bend_s)

    # Re-calculate L_OUTER_STRAIGHT for correct X_TOTAL
    remaining_x = X_TOTAL - L_BARS_SECTION - (2 * L_TRANSITION_X) # 18.24 - 8.5 - 4.0 = 5.74
    L_OUTER_STRAIGHT = (remaining_x - 2 * R_END_CAP) / 2 # (5.74 - 2*0.15) / 2 = (5.74 - 0.3) / 2 = 5.44 / 2 = 2.72

    # --- Cross-sections ---
    xs_outer = gf.cross_section.cross_section(width=W_OUTER_ARM, layer=LAYER)
    xs_inner = gf.cross_section.cross_section(width=W_INNER_ARM, layer=LAYER)

    # --- Add Top Arm ---
    top_arm_comp = c << create_single_arm(
        y_outer_center=Y_OUTER_CENTER_TOP,
        dy_vertical_shift=DY_VERTICAL_SHIFT,
        xs_outer=xs_outer,
        xs_inner=xs_inner,
        l_outer_straight=L_OUTER_STRAIGHT,
        l_bars_section=L_BARS_SECTION,
        l_transition_x=L_TRANSITION_X,
        r_end_cap=R_END_CAP,
        bar_width=BAR_WIDTH,
        bar_pitch=BAR_PITCH,
        n_bars=N_BARS,
        bar_height_slot=BAR_HEIGHT_SLOT,
        layer=LAYER,
        mirror_y=False
    )

    # --- Add Bottom Arm ---
    bottom_arm_comp = c << create_single_arm(
        y_outer_center=Y_OUTER_CENTER_BOTTOM,
        dy_vertical_shift=DY_VERTICAL_SHIFT,
        xs_outer=xs_outer,
        xs_inner=xs_inner,
        l_outer_straight=L_OUTER_STRAIGHT,
        l_bars_section=L_BARS_SECTION,
        l_transition_x=L_TRANSITION_X,
        r_end_cap=R_END_CAP,
        bar_width=BAR_WIDTH,
        bar_pitch=BAR_PITCH,
        n_bars=N_BARS,
        bar_height_slot=BAR_HEIGHT_SLOT,
        layer=LAYER,
        mirror_y=True
    )

    # --- Add Central Isolated Rectangle ---
    W_CENTRAL_BLOCK = 0.2
    H_CENTRAL_BLOCK = 0.1
    
    # A simple X position to visually match the image:
    central_rect_x = X_TOTAL / 2 - R_END_CAP - L_OUTER_STRAIGHT/2 - W_CENTRAL_BLOCK/2
    central_rect_x -= 0.5 # Shift slightly left for better visual match

    central_rect = c << gf.components.rectangle(
        size=(W_CENTRAL_BLOCK, H_CENTRAL_BLOCK),
        layer=LAYER,
        centered=True
    )
    central_rect.center = (central_rect_x, Y_CENTER_LINE)

    return c

# --- Script Execution ---
if __name__ == "__main__":
    device = device_from_image()
    device.show()
    device.write_gds("device_from_image_fixed.gds")