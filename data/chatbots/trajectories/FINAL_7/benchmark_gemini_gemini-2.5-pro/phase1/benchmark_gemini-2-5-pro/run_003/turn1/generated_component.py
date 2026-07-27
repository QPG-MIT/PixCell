import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device geometry by performing a boolean subtraction
    of cutout shapes from a solid racetrack base.
    """
    # --------------------------------------------------------------------------
    # 1. Define Device Parameters based on footprint and image analysis
    # --------------------------------------------------------------------------
    footprint_width = 3.0
    footprint_length = 5.5

    # Proportional dimensions derived from visual inspection of the image
    bar_height = 0.7  # Height of the two horizontal bars
    center_gap = 0.4  # Gap between the two horizontal bars
    ring_thickness_side = 0.4  # Width of the connection to the outer ring on the left/right
    ring_thickness_top = 0.3 # Thickness of the ring at the top/bottom

    # Dimensions for the small square cutouts in the bars
    hole_size = (0.5, 0.5)
    hole_spacing = 0.3  # Horizontal space between the two holes in a bar

    # --------------------------------------------------------------------------
    # 2. Create the solid base body (a racetrack/stadium shape)
    # --------------------------------------------------------------------------
    # FIX: Reverted from the non-existent 'racetrack' component back to the
    # original boolean construction method. The 'locked cell' RuntimeError is
    # now fixed by using .copy() to create a new, movable instance of the
    # circle component before applying the .movex() transformation.
    base_radius = footprint_width / 2.0
    base_length_straight = footprint_length - 2 * base_radius

    base_rect = gf.components.rectangle(
        size=(base_length_straight, footprint_width)
    )
    base_disk = gf.components.circle(radius=base_radius)

    # Union the rectangle and two copied/moved disks to form the solid base
    base_with_disk1 = gf.boolean(
        base_rect, base_disk.copy().movex(-base_length_straight / 2.0), operation="or"
    )
    base_solid = gf.boolean(
        base_with_disk1, base_disk.copy().movex(base_length_straight / 2.0), operation="or"
    )

    # --------------------------------------------------------------------------
    # 3. Create the cutout geometry to be subtracted
    # --------------------------------------------------------------------------
    cutouts = gf.Component("cutouts")

    # a) Create the two large voids (also as racetracks)
    void_length_straight = base_length_straight - 2 * ring_thickness_side
    outer_gap_height = (footprint_width - 2*ring_thickness_top - 2*bar_height - center_gap) / 2
    void_radius = outer_gap_height / 2.0
    void_y_center = center_gap / 2.0 + bar_height + outer_gap_height / 2.0

    # FIX: Also applied the .copy() fix to the construction of the inner voids.
    void_rect = gf.components.rectangle(
        size=(void_length_straight, outer_gap_height)
    )
    void_disk = gf.components.circle(radius=void_radius)
    void_with_disk1 = gf.boolean(
        void_rect, void_disk.copy().movex(-void_length_straight / 2.0), operation="or"
    )
    void_racetrack = gf.boolean(
        void_with_disk1, void_disk.copy().movex(void_length_straight / 2.0), operation="or"
    )

    # Add the top and bottom voids to the cutouts component
    cutouts.add_ref(void_racetrack).movey(void_y_center)
    cutouts.add_ref(void_racetrack).movey(-void_y_center)

    # b) Create the four small square holes
    hole = gf.components.rectangle(size=hole_size, centered=True)
    hole_x_pos = (hole_size[0] + hole_spacing) / 2.0
    hole_y_pos = center_gap / 2.0 + bar_height / 2.0

    # Add the four holes to the cutouts component
    cutouts.add_ref(hole).move((hole_x_pos, hole_y_pos))
    cutouts.add_ref(hole).move((-hole_x_pos, hole_y_pos))
    cutouts.add_ref(hole).move((hole_x_pos, -hole_y_pos))
    cutouts.add_ref(hole).move((-hole_x_pos, -hole_y_pos))

    # --------------------------------------------------------------------------
    # 4. Perform the final boolean subtraction
    # --------------------------------------------------------------------------
    device = gf.boolean(A=base_solid, B=cutouts, operation="not")
    
    # Final component setup
    c = gf.Component()
    c.add_ref(device)
    c.flatten() # Combine all polygons into a single cell
    return c

# Main execution block to generate and display the GDS
if __name__ == "__main__":
    # Instantiate the component
    my_device = create_device()

    # Show the component in the KLayout viewer
    my_device.show()