import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device geometry based on the provided image, using parametric
    GDSFactory functions.

    The method involves three main steps:
    1.  Define the top U-shaped component by creating a solid shape and then
        subtracting four curved slots using a boolean operation. This ensures
        the lines emerge smoothly from a solid central bar.
    2.  Define the central part as a simple 5-line straight coupler.
    3.  Assemble the final device by placing the top component, the central
        coupler, and a mirrored version of the top component for the bottom.
    """
    c = gf.Component("FinalDevice")

    # --- 1. Define Device Parameters ---

    # Overall dimensions from footprint constraint
    device_width = 120.0
    
    # Parameters for the top and bottom U-shaped structures
    u_shape_total_height = 1.0
    u_shape_straight_len = 80.0
    u_shape_bend_dy = 0.2  # Vertical displacement of the arms
    num_lines_u_shape = 5
    slot_width = 0.12
    # Calculate the width of the material between slots based on total height
    material_width = (u_shape_total_height - (num_lines_u_shape - 1) * slot_width) / num_lines_u_shape
    line_pitch = material_width + slot_width

    # Parameters for the central 5-line coupler
    coupler_line_width = 0.12
    coupler_gap = 0.12
    coupler_pitch = coupler_line_width + coupler_gap
    coupler_total_height = 5 * coupler_line_width + 4 * coupler_gap

    # Vertical positioning parameters
    vertical_gap_between_sections = 0.2
    y_center_coupler = 0.0
    y_center_u_shape = coupler_total_height / 2 + vertical_gap_between_sections + u_shape_total_height / 2

    # --- 2. Create the Top U-Shaped Component ---

    # Define the x-coordinates for the smooth path waypoints
    x_outer = -device_width / 2
    x_inner = -u_shape_straight_len / 2
    
    # Define the y-coordinates for the path's centerline
    y_bar_center = y_center_u_shape
    y_arm_center = y_bar_center + u_shape_bend_dy

    # Create the solid U-shaped base for the boolean operation
    points_solid = [
        (x_outer, y_arm_center),
        (x_inner, y_bar_center),
        (-x_inner, y_bar_center),
        (-x_outer, y_arm_center),
    ]
    path_solid = gf.path.smooth(points=points_solid, radius=15)
    U_solid = gf.path.extrude(path_solid, width=u_shape_total_height, layer=(1, 0))

    # Create the four curved slots to be subtracted
    slots_container = gf.Component("slots_to_subtract")
    num_slots = num_lines_u_shape - 1
    slot_center_offsets = [(i - (num_slots - 1) / 2) * line_pitch for i in range(num_slots)]

    for offset in slot_center_offsets:
        y_bar_slot = y_bar_center + offset
        y_arm_slot = y_arm_center + offset
        points_slot = [
            (x_outer, y_arm_slot),
            (x_inner, y_bar_slot),
            (-x_inner, y_bar_slot),
            (-x_outer, y_arm_slot),
        ]
        path_slot = gf.path.smooth(points=points_slot, radius=15)
        slot = gf.path.extrude(path_slot, width=slot_width, layer=(1, 0))
        slots_container.add_ref(slot)

    # Perform the boolean 'not' operation to cut the slots
    top_component = gf.boolean(A=U_solid, B=slots_container, operation="not", layer=(1, 0))

    # --- 3. Create the Central Coupler ---
    
    # FIX: Define a cross_section for the central waveguides. This bundles the
    # width and layer information, which is the correct way to parameterize
    # components like 'straight'.
    coupler_xs = gf.cross_section.cross_section(width=coupler_line_width, layer=(1, 0))
    
    central_coupler = gf.Component("central_coupler")
    num_lines_coupler = 5
    coupler_y_offsets = [
        (i - (num_lines_coupler - 1) / 2) * coupler_pitch for i in range(num_lines_coupler)
    ]
    for offset in coupler_y_offsets:
        # FIX: Pass the defined 'coupler_xs' cross_section to the straight component.
        wg = central_coupler.add_ref(
            gf.components.straight(length=device_width, cross_section=coupler_xs)
        )
        wg.movey(y_center_coupler + offset)

    # --- 4. Assemble the Final Device ---
    
    # Add the top component
    c.add_ref(top_component)

    # Create and add the bottom component by mirroring the top one
    bottom_component = top_component.copy()
    bottom_component.mirror(p1=(0, 0), p2=(1, 0))
    c.add_ref(bottom_component)
    
    # Add the central coupler
    c.add_ref(central_coupler)

    return c

# Instantiate the cell to create the component
device = create_device()

# The following line saves the component to a GDS file.
device.write_gds("output.gds")
print("GDS file saved as 'output.gds'")