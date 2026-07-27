import gdsfactory as gf

@gf.cell
def custom_image_device():
    c = gf.Component("racetrack_multi_line")

    # Parameters for the lines and gaps
    line_width = 0.5  # Width of each black line
    gap = 0.5         # Width of each white space (between black lines)

    # Define the custom cross-section with 4 parallel lines.
    # The 'CrossSection' object itself does not have an 'add' method for sections anymore.
    # Instead, you pass a list of 'gf.Section' objects to its 'sections' parameter.

    # Calculate offsets such that the entire 4-line structure (3.5um tall) is centered around the path's spine (y=0)
    # Total height of 4 lines + 3 gaps = (4 * line_width) + (3 * gap) = (4 * 0.5) + (3 * 0.5) = 2.0 + 1.5 = 3.5 um.
    # To center this 3.5um block around y=0, its bottom edge will be at -1.75um and top edge at +1.75um.
    # The center of each 0.5um line relative to y=0:
    # Line 1 (bottom): Center at -1.75 + (0.5/2) = -1.75 + 0.25 = -1.5
    # Line 2: Center at -1.75 + 0.5 (line 1 height) + 0.5 (gap) + (0.5/2) (half line 2 height) = -1.75 + 0.5 + 0.5 + 0.25 = -0.5
    # Line 3: Center at -1.75 + 0.5 + 0.5 + 0.5 + 0.5 + (0.5/2) = -1.75 + 2.0 + 0.25 = 0.5
    # Line 4 (top): Center at -1.75 + 0.5 + 0.5 + 0.5 + 0.5 + 0.5 + 0.5 + (0.5/2) = -1.75 + 3.0 + 0.25 = 1.5

    sections_list = [
        gf.Section(width=line_width, offset=-1.5, layer=(1, 0)),
        gf.Section(width=line_width, offset=-0.5, layer=(1, 0)),
        gf.Section(width=line_width, offset=0.5, layer=(1, 0)),
        gf.Section(width=line_width, offset=1.5, layer=(1, 0)),
    ]

    # Create the CrossSection instance by passing the list of sections
    xs = gf.CrossSection(sections=sections_list) 

    # Path parameters for the spine of the racetrack shape
    # The overall footprint is 120.0 um x 4.0 um.
    # The `xs` (cross-section) has a total height of 3.5 um.
    # For the extruded component to have a total height of 4.0 um,
    # the path's vertical span must be 4.0 - 3.5 = 0.5 um.
    # Since the image shows smooth corners and no apparent straight vertical segments for the path,
    # we choose `R_bend = 0.5 / 2 = 0.25 um`. This implies the path only consists of horizontal segments and bends.
    R_bend = 0.25  # Radius of the path's spine bends for the rounded corners.

    # Create the path that the custom cross-section will follow.
    # This path forms a closed racetrack shape.
    # We define waypoints for a rectangle that spans from x=0 to x=120, and y=-0.25 to y=0.25.
    # `gf.path.smooth` with appropriate points and radius will create a rounded rectangle.
    
    # Points for a 120um x 0.5um rectangle, centered around y=0, with corners to be smoothed.
    # The x-coordinates define the inner edge of the bend where the straight section begins/ends.
    # The y-coordinates define the top/bottom edge of the path's central spine.
    path_points = [
        (R_bend, -0.25),          # Bottom-left nominal corner (start of straight after bend)
        (R_bend, 0.25),           # Top-left nominal corner
        (120.0 - R_bend, 0.25),     # Top-right nominal corner
        (120.0 - R_bend, -0.25),    # Bottom-right nominal corner
        (R_bend, -0.25)           # Close the loop
    ]
    
    # gf.path.smooth will connect these points with arcs of radius `R_bend`.
    path_spine = gf.path.smooth(points=path_points, radius=R_bend)

    # Extrude the path with the custom cross-section
    device = gf.path.extrude(path_spine, cross_section=xs)

    # Add the extruded device reference to the main component
    c.add_ref(device)

    # The `path_spine` created by `gf.path.smooth` (with R_bend=0.25)
    # for `path_points` (from x=0 to x=120, y=-0.25 to y=0.25)
    # will have a bounding box of `(0, 120)` for x and `(-0.25, 0.25)` for y.
    # This path is implicitly centered at (60,0) based on its defined points.
    # The `xs` has a total height of 3.5 um, centered on the path spine.
    # When extruded, the final component's bounding box will be:
    # x_min = path_spine.xmin = 0
    # x_max = path_spine.xmax = 120
    # y_min = path_spine.ymin - (xs_total_height / 2) = -0.25 - (3.5 / 2) = -0.25 - 1.75 = -2.0
    # y_max = path_spine.ymax + (xs_total_height / 2) = 0.25 + (3.5 / 2) = 0.25 + 1.75 = 2.0
    # This results in a component of size `120 um x 4.0 um`, perfectly matching the footprint constraint.

    return c

# Create and save the GDS file
if __name__ == "__main__":
    device_component = custom_image_device()
    device_component.write_gds("racetrack_multi_line.gds")
    print(f"Generated GDS file: racetrack_multi_line.gds")
    # To view the generated GDS in KLayout or similar software, uncomment the line below:
    # device_component.show()