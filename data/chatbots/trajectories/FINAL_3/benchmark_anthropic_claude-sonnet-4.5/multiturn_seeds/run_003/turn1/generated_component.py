import gdsfactory as gf

@gf.cell
def interlocking_structures():
    c = gf.Component()
    
    # Parameters
    total_width = 120.0
    total_height = 4.0
    line_width = 0.6  # Width of the traces
    side_extension = 12.0  # Length of horizontal extensions
    vertical_drop = 1.5  # How far down/up the structures go
    bend_radius = 1.8  # Radius for smooth corners
    
    # Create cross-section for the waveguides
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    
    # Top structure: starts high on left, drops down, goes across, rises up, ends high on right
    y_top = -0.3
    y_middle_top = y_top - vertical_drop
    
    points_top = [
        (0, y_top),
        (side_extension, y_top),
        (side_extension + bend_radius, y_middle_top),
        (total_width - side_extension - bend_radius, y_middle_top),
        (total_width - side_extension, y_top),
        (total_width, y_top)
    ]
    
    path_top = gf.path.smooth(points=points_top, radius=bend_radius)
    wg_top = path_top.extrude(xs)
    c << wg_top
    
    # Bottom structure: starts low on left, rises up, goes across, drops down, ends low on right
    y_bottom = -total_height + 0.3
    y_middle_bottom = y_bottom + vertical_drop
    
    points_bottom = [
        (0, y_bottom),
        (side_extension, y_bottom),
        (side_extension + bend_radius, y_middle_bottom),
        (total_width - side_extension - bend_radius, y_middle_bottom),
        (total_width - side_extension, y_bottom),
        (total_width, y_bottom)
    ]
    
    path_bottom = gf.path.smooth(points=points_bottom, radius=bend_radius)
    wg_bottom = path_bottom.extrude(xs)
    c << wg_bottom
    
    return c

# Create and save the device
device = interlocking_structures()
device.show()  # Optional: display in viewer
device.write_gds("interlocking_structures.gds")