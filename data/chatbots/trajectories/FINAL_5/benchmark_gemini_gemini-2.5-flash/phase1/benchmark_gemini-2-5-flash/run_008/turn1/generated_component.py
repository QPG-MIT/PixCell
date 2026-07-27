import gdsfactory as gf

@gf.cell
def device_from_image():
    c = gf.Component("device_from_image")

    # --- Device Dimensions ---
    X_TOTAL = 18.24  # Total device width
    Y_TOTAL = 0.7    # Total device height

    W_ARM = 0.2      # Width of the main arms
    W_CENTER = 0.1   # Width of the central line and vertical bars
    G_ARM_INNER = 0.05 # Gap between central line and the inner edge of the main arm

    # --- Central Y-coordinate (Corrected definition and placement) ---
    # The device is centered vertically, so the central line is at Y=0.
    Y_CENTER_LINE = 0.0

    # --- Derived Y-coordinates for component centerlines ---
    # Y_INNER_TOP_ARM_CENTER: Centerline of the straight segment of the top arm that has bars.
    Y_INNER_TOP_ARM_CENTER = Y_CENTER_LINE + W_CENTER / 2 + G_ARM_INNER + W_ARM / 2  # 0.0 + 0.05 + 0.05 + 0.1 = 0.2 µm
    
    # Y_OUTER_TOP_ARM_CENTER: Centerline of the outermost straight segments of the top arm (and the tips).
    Y_OUTER_TOP_ARM_CENTER = Y_TOTAL / 2 - W_ARM / 2  # 0.35 - 0.1 = 0.25 µm

    # DY_BEND: The vertical displacement of the S-bends
    DY_BEND = Y_OUTER_TOP_ARM_CENTER - Y_INNER_TOP_ARM_CENTER  # 0.25 - 0.2 = 0.05 µm

    # Coordinates for the bottom arm (symmetrical to top arm)
    Y_INNER_BOTTOM_ARM_CENTER = -Y_INNER_TOP_ARM_CENTER
    Y_OUTER_BOTTOM_ARM_CENTER = -Y_OUTER_TOP_ARM_CENTER

    # --- Feature Dimensions (derived from image and total dimensions) ---
    L_TIP = 0.5      # Length of the pointed tips (tapers)
    N_BARS = 29      # Number of vertical bars in each arm
    BAR_WIDTH = W_CENTER  # Width of each vertical bar
    BAR_GAP = 0.2    # Gap between vertical bars (estimated for visual fit)
    
    # L_BARS_SECTION: Total horizontal length occupied by bars and their gaps
    # For N_BARS bars, there are (N_BARS-1) gaps.
    L_BARS_SECTION = N_BARS * BAR_WIDTH + (N_BARS - 1) * BAR_GAP # 29*0.1 + 28*0.2 = 2.9 + 5.6 = 8.5 µm

    R_S_BEND_DX = 2.0  # Horizontal length of the S-bends

    # L_S_END: Length of the straight segments at the outer ends of the arms.
    # X_TOTAL = 2 * L_TIP + 2 * L_S_END + 2 * R_S_BEND_DX + L_BARS_SECTION
    # 18.24 = 2*0.5 + 2*L_S_END + 2*2.0 + 8.5  =>  18.24 = 1.0 + 2*L_S_END + 4.0 + 8.5
    # 18.24 = 13.5 + 2*L_S_END  =>  2*L_S_END = 4.74  =>  L_S_END = 2.37 µm
    L_S_END = 2.37

    # --- Cross-sections ---
    xs_arm = gf.cross_section.cross_section(width=W_ARM, layer=(1, 0))
    xs_center = gf.cross_section.cross_section(width=W_CENTER, layer=(1, 0))

    # --- Add Central Line ---
    center_line_comp = c << gf.components.straight(length=X_TOTAL, cross_section=xs_center)
    center_line_comp.center = (0, Y_CENTER_LINE) # Place it at (0,0)

    # --- Helper function to create an arm (top or bottom) ---
    @gf.cell
    def create_arm(y_outer_center, dy_bend_value, y_inner_center_for_bars):
        arm_c = gf.Component()
        
        # Calculate the starting X-coordinate for the arm's path
        # This will be the global left edge of the device, relative to the arm's local origin.
        x_start_coord_local = -X_TOTAL / 2 

        # 1. Left Tip (taper from W_ARM to 0 width)
        tip_left = arm_c << gf.components.taper(length=L_TIP, width1=W_ARM, width2=0, cross_section=xs_arm)
        tip_left.rotate(180) # Rotate to make the taper point left
        # Position the right (wide) end of the taper at the start of the first straight segment
        tip_left.movex(x_start_coord_local + L_TIP)
        tip_left.movey(y_outer_center)
        
        # 2. Outer Left Straight
        s_outer_left = arm_c << gf.components.straight(length=L_S_END, cross_section=xs_arm)
        s_outer_left.connect("o1", tip_left.ports["o2"])

        # 3. First S-bend (moves arm vertically inwards)
        bend_in = arm_c << gf.components.bend_s(size=(R_S_BEND_DX, dy_bend_value), cross_section=xs_arm)
        bend_in.connect("o1", s_outer_left.ports["o2"])

        # 4. Inner Middle Straight (section containing the vertical bars)
        s_inner_middle = arm_c << gf.components.straight(length=L_BARS_SECTION, cross_section=xs_arm)
        s_inner_middle.connect("o1", bend_in.ports["o2"])

        # 5. Place the vertical bars (rectangles)
        # Bars are centered vertically on the inner straight section
        # The first bar's left edge starts at the beginning of s_inner_middle
        for i in range(N_BARS):
            bar = arm_c << gf.components.rectangle(size=(BAR_WIDTH, W_ARM), layer=(1, 0), centered=True)
            # Calculate x-center for each bar
            bar_x_center = s_inner_middle.ports["o1"].x + (i * (BAR_WIDTH + BAR_GAP)) + BAR_WIDTH / 2
            bar.center = (bar_x_center, y_inner_center_for_bars)

        # 6. Second S-bend (moves arm vertically outwards)
        # Negative dy_bend_value to reverse the bend direction and bring it back to the outer y_position
        bend_out = arm_c << gf.components.bend_s(size=(R_S_BEND_DX, -dy_bend_value), cross_section=xs_arm) 
        bend_out.connect("o1", s_inner_middle.ports["o2"])

        # 7. Outer Right Straight
        s_outer_right = arm_c << gf.components.straight(length=L_S_END, cross_section=xs_arm)
        s_outer_right.connect("o1", bend_out.ports["o2"])

        # 8. Right Tip (taper from W_ARM to 0 width)
        tip_right = arm_c << gf.components.taper(length=L_TIP, width1=W_ARM, width2=0, cross_section=xs_arm)
        tip_right.connect("o1", s_outer_right.ports["o2"])

        return arm_c

    # --- Add Top Arm ---
    top_arm_comp = c << create_arm(
        Y_OUTER_TOP_ARM_CENTER, 
        DY_BEND, # Positive dy_bend_value for top arm (bends downwards towards Y_INNER)
        Y_INNER_TOP_ARM_CENTER
    )

    # --- Add Bottom Arm ---
    bottom_arm_comp = c << create_arm(
        Y_OUTER_BOTTOM_ARM_CENTER, 
        -DY_BEND, # Negative dy_bend_value for bottom arm (bends upwards towards Y_INNER)
        Y_INNER_BOTTOM_ARM_CENTER
    )

    return c

# --- Script Execution ---
if __name__ == "__main__":
    device = device_from_image()
    device.show() # Display the generated GDS in KLayout (if installed and configured)
    device.write_gds("device_from_image.gds") # Save the GDS file