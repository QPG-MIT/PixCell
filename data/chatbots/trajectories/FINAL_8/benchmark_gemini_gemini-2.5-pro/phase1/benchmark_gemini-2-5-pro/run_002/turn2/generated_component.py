import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the new asymmetric device geometry based on the provided image.

    The method involves three distinct steps:
    1.  Create the top-left section, which consists of three parallel lines
        following a mitered path. This is done by defining a path from a list
        of points and extruding it.
    2.  Create the central-right section, a simple block of five parallel
        straight waveguides.
    3.  Assemble the final device by instantiating the top section, creating a
        mirrored version for the bottom section, instantiating the central
        section, and arranging all three in their correct asymmetric positions.
    """
    c = gf.Component("FinalDevice")

    # --- 1. Define Common Parameters ---
    line_width = 2.0
    gap = 2.0
    pitch = line_width + gap
    layer_spec = (1, 0)

    # --- 2. Create the Top/Bottom Mitered Section Sub-Component ---
    mitered_component = gf.Component("MiteredSection")
    num_lines_mitered = 3

    # Define the path for a single mitered line using waypoints
    # The path consists of straight horizontal and diagonal segments
    path_points = [
        (0, 0),
        (15, 0),
        (20, -5),
        (35, -5),
        (40, -10),
        (55, -10)
    ]
    mitered_path = gf.Path(path_points)

    # Create a cross_section for this path
    xs = gf.cross_section.cross_section(width=line_width, layer=layer_spec)

    # Create the three parallel lines by extruding the same path at different offsets
    for i in range(num_lines_mitered):
        # Extrude the path to create a single waveguide component
        waveguide = gf.path.extrude(mitered_path, cross_section=xs)
        # Add a reference to this waveguide in our mitered_component
        ref = mitered_component.add_ref(waveguide)
        # Move it vertically to create the stack
        ref.movey(i * pitch)

    # --- 3. Create the Central Straight Section Sub-Component ---
    straight_component = gf.Component("StraightSection")
    num_lines_straight = 5
    straight_length = 40.0

    # Create and arrange the five parallel straight waveguides
    for i in range(num_lines_straight):
        wg = straight_component.add_ref(
            gf.components.straight(length=straight_length, cross_section=xs)
        )
        wg.movey(i * pitch)
    # Center the origin of this component vertically for easier placement
    straight_component.movey(-straight_component.ysize / 2)

    # --- 4. Assemble the Final Device ---

    # Instantiate and place the top-left section
    top_ref = c.add_ref(mitered_component)
    top_ref.move(origin=(-50, 25))

    # Instantiate, mirror, and place the bottom-left section
    bottom_ref = c.add_ref(mitered_component)
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the x-axis
    bottom_ref.move(origin=(-50, -25))

    # Instantiate and place the central-right section
    central_ref = c.add_ref(straight_component)
    central_ref.move(origin=(20, 0))
    
    return c

# Instantiate the cell to create the component
device = create_device()

# Save the component to a GDS file.
device.write_gds("output.gds")
print("GDS file saved as 'output.gds'")