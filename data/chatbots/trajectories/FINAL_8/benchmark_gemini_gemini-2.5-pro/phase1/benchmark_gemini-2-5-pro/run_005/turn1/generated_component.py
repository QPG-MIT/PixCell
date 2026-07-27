import gdsfactory as gf

@gf.cell
def create_device():
    """Creates the full device by assembling the central and outer structures."""
    
    # 1. Define device parameters to match the footprint and image proportions.
    
    # Vertical dimensions
    line_width = 0.1
    line_gap = 0.1
    bar_width = 0.5
    bar_gap = 0.1
    main_gap = 0.05

    # Horizontal dimensions to match 120um width
    bend_radius = 10.0
    center_straight_length = 100.0
    
    # This parameter is for the vertical waveguide section after the bend
    end_straight_length = 10.0
    
    # 2. Create the central bundle of 5 straight waveguides.
    c = gf.Component("final_device")
    
    central_lines = gf.Component("central_lines")
    pitch = line_width + line_gap
    num_lines = 5
    
    # Center the group of 5 lines around y=0
    initial_y_center = -(num_lines - 1) / 2 * pitch
    for i in range(num_lines):
        wg = central_lines << gf.components.straight(
            length=center_straight_length,
            width=line_width,
            cross_section="strip"
        )
        wg.movey(initial_y_center + i * pitch)

    # 3. Create the path for a single top-right corner piece.
    # This path will be reused for all lines in the outer structure.
    path = gf.Path()
    path.append(gf.path.straight(length=center_straight_length / 2))
    path.append(gf.path.euler(radius=bend_radius, angle=90))
    path.append(gf.path.straight(length=end_straight_length))

    # 4. Build the top-right corner piece by extruding the path for each line.
    corner_piece = gf.Component("corner_piece")
    
    # Calculate y-offsets for the 5 thin lines, centered around y=0
    initial_y_outer = -(num_lines - 1) / 2 * pitch
    
    # Add the 5 thin lines by extruding the path and moving them.
    first_ref = None
    for i in range(num_lines):
        p = gf.path.extrude(path, width=line_width)
        ref = corner_piece << p
        ref.movey(initial_y_outer + i * pitch)
        if i == 0:
            first_ref = ref # Store a reference to one of the parts to get ports from

    # Calculate y-offset for the thick bar.
    bar_offset = initial_y_outer - line_width/2 - bar_gap - bar_width/2
    
    # Add the thick bar.
    p_bar = gf.path.extrude(path, width=bar_width)
    corner_piece << p_bar
    p_bar.movey(bar_offset)

    # Add ports to the corner_piece component so it can be connected.
    # We can take the ports from any of the internal extruded parts.
    corner_piece.add_port("o1", port=first_ref.ports["o1"])
    corner_piece.add_port("o2", port=first_ref.ports["o2"])

    # 5. Assemble the full top structure from two mirrored corner pieces.
    top_structure = gf.Component("top_structure")
    
    tr_corner = top_structure << corner_piece
    tl_corner = top_structure << corner_piece.mirror()
    
    # Use connect() to perfectly align the two halves at the center.
    tl_corner.connect("o1", tr_corner.ports["o1"])
    
    # 6. Assemble the final device.
    
    # Add the central lines, which are already centered at (0,0).
    c << central_lines

    # Add the top structure and a vertically mirrored copy for the bottom.
    top_ref = c << top_structure
    bottom_ref = c << top_structure.mirror(p1=(0, 0), p2=(1, 0))

    # Calculate the required vertical shift to create the main gap.
    central_group_height = (num_lines * line_width) + ((num_lines - 1) * line_gap)
    outer_lines_height = central_group_height
    
    y_shift = (central_group_height / 2) + main_gap + (outer_lines_height / 2)
    
    # Position the top and bottom structures.
    top_ref.movey(y_shift)
    bottom_ref.movey(-y_shift)
    
    return c

# Instantiate and show the component.
device = create_device()
device.show()