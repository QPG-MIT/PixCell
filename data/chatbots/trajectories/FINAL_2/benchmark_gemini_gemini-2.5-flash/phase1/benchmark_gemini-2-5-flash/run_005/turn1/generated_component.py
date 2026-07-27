import gdsfactory as gf

@gf.cell
def device_from_image(layer=(1,0)):
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.
    The device is designed to fit a 25x10 um footprint, centered at (0,0).
    """
    c = gf.Component("device_from_image")

    W_total = 25
    H_total = 10

    # List to collect all positioned references for the final boolean operation
    all_parts_refs = []

    # 1. Main rectangular block
    H_main_rect = 6
    # Creates a rectangle centered at (0,0). Its y-span will be [-3, 3].
    main_rect_g = gf.components.rectangle(size=(W_total, H_main_rect), layer=layer, centered=True)
    main_rect_ref = c.add_ref(main_rect_g) # Adding this directly is fine as it's not being transformed
    all_parts_refs.append(main_rect_ref)

    # 2. Bottom Notch
    H_notch = 2
    W_notch_top = 4    # Width at y=-3 (where it meets main_rect)
    W_notch_bottom = 2 # Width at y=-5 (bottom of device)

    # Create a base taper component (cached by GDSFactory)
    base_notch_taper = gf.components.taper(
        length=H_notch,
        width1=W_notch_bottom,  # Narrower width at the bottom (y=-5)
        width2=W_notch_top,     # Wider width at the top (y=-3)
        layer=layer,
    )
    # Create a mutable copy and then apply transformations to the copy
    notch_comp_transformed = base_notch_taper.copy()
    notch_comp_transformed.rotate(angle=-90)
    # Its current y-span is [0, 2] (after rotation). We want [-5, -3].
    # Move its y_min from 0 to -5.
    notch_comp_transformed.movey(-5) 
    
    notch_ref = c.add_ref(notch_comp_transformed)
    all_parts_refs.append(notch_ref)


    # 3. Define a single finger component (will be used for multiple instances)
    H_finger_base = 0.5
    W_finger_base = 3
    H_finger_taper = 1.5 # Total finger height = H_finger_base + H_finger_taper = 0.5 + 1.5 = 2.0
    W_finger_tip = 1

    temp_single_finger_comp = gf.Component("temp_single_finger")
    
    # Finger base (rectangle)
    base_finger_rect = gf.components.rectangle(
        size=(W_finger_base, H_finger_base),
        layer=layer,
        centered=True # Default y-span [-0.25, 0.25]
    )
    # Add a copy as a reference to the temporary component
    fb_ref_temp = temp_single_finger_comp.add_ref(base_finger_rect.copy())

    # Finger taper (rotated taper)
    # Create base taper (cached)
    base_finger_taper = gf.components.taper(
        length=H_finger_taper,
        width1=W_finger_base, # Wider width at the bottom of the taper
        width2=W_finger_tip,  # Narrower width at the top of the taper
        layer=layer,
    )
    # Create a mutable copy and apply rotation
    finger_taper_comp_transformed = base_finger_taper.copy()
    finger_taper_comp_transformed.rotate(angle=90)

    # Add a reference to this transformed component to the temporary single finger component
    ft_ref_temp = temp_single_finger_comp.add_ref(finger_taper_comp_transformed)

    # Align the taper's bottom (ymin=0 after rotation, before moving reference) with the base's top (ymax=0.25)
    # This move is applied to the *reference*, which is allowed.
    ft_ref_temp.movey(fb_ref_temp.ymax - ft_ref_temp.ymin)
    # Now, fb_ref_temp y-span: [-0.25, 0.25]
    # ft_ref_temp y-span: [0.25, 1.75]
    # So `temp_single_finger_comp` overall y-span is [-0.25, 1.75], total height = 2.


    # 4. Place four instances of the single finger component
    finger_y_min_target = 3 # Fingers start at y=3 (top of main_rect)
    # Calculate the y-offset to move the `temp_single_finger_comp`
    # Its current y_min is -0.25. Desired y_min is 3. Move amount: 3 - (-0.25) = 3.25.
    finger_move_y = 3.25

    num_fingers = 4
    total_finger_width = num_fingers * W_finger_base # 4 * 3 = 12 µm
    remaining_space = W_total - total_finger_width   # 25 - 12 = 13 µm
    num_gaps = num_fingers - 1 + 2 # 3 inner gaps + 2 outer gaps = 5 gaps
    gap_width = remaining_space / num_gaps           # 13 / 5 = 2.6 µm per gap

    # Calculate x-center positions for each finger
    finger_x_centers = []
    # Start at -W_total/2, add first outer gap, then half finger width to get first center
    current_x = -W_total/2 + gap_width + W_finger_base/2
    for i in range(num_fingers):
        finger_x_centers.append(current_x)
        current_x += W_finger_base + gap_width # Move to next finger center

    # Add finger references to the main component
    for x_center in finger_x_centers:
        # Move is applied to the reference, which is allowed.
        finger_ref = c.add_ref(temp_single_finger_comp).move((x_center, finger_move_y))
        all_parts_refs.append(finger_ref)
    # Each placed finger reference will now span y:[3, 5].


    # 5. Perform a single boolean "or" operation on all collected references
    final_geometry_comp = gf.boolean(all_parts_refs, operation="or", layer=layer)

    # Add the final combined geometry (as a reference) to the main component `c`
    c.add_ref(final_geometry_comp)

    # Cleanup: remove all individual references used for boolean operation from `c`
    for part_ref in all_parts_refs:
        c.remove(part_ref)
    
    return c

# Create the device component
device = device_from_image()

# Write the GDS file
device.write_gds("device_from_image.gds")

# Optional: Display the device for visual verification and print its bounding box
# device.show()
# print(f"Device bounds: {device.dbbox()}")
# Expected output for bounds: DBox(xmin=-12.5, ymin=-5.0, xmax=12.5, ymax=5.0)