import gdsfactory as gf

@gf.cell
def create_device():
    """
    Recreates the specified geometry using parametric gdsfactory components
    and a final boolean union operation.
    """

    # Create a temporary component to hold the primitive shapes before merging.
    tmp = gf.Component("primitives")

    # Define geometric parameters based on the 25x10 um footprint.
    main_rect_width = 25.0
    main_rect_height = 5.0

    bottom_tab_height = 1.0
    bottom_tab_top_width = 5.0
    bottom_tab_bottom_width = 2.0

    num_prongs = 4
    prong_base_width = 4.0
    prong_tip_width = 2.0
    prong_taper_height = 2.0
    prong_straight_height = 2.0

    # Calculate Y-positions, building the device from y=0 upwards.
    y_tab_center = bottom_tab_height / 2.0
    y_rect_bottom = bottom_tab_height
    y_rect_center = y_rect_bottom + main_rect_height / 2.0
    y_prongs_base = y_rect_bottom + main_rect_height

    # Calculate X-positions for the evenly spaced prongs.
    prong_spacing = main_rect_width / num_prongs
    x_start = -main_rect_width / 2 + prong_spacing / 2
    x_positions = [x_start + i * prong_spacing for i in range(num_prongs)]

    # 1. Create and place the main rectangular body.
    main_rect = gf.components.rectangle(
        size=(main_rect_width, main_rect_height), centered=True
    )
    rect_ref = tmp << main_rect
    rect_ref.movey(y_rect_center)

    # 2. Create and place the bottom tab (a rotated taper).
    bottom_tab = gf.components.taper(
        length=bottom_tab_height,
        width1=bottom_tab_top_width,
        width2=bottom_tab_bottom_width,
    )
    tab_ref = tmp << bottom_tab
    tab_ref.rotate(-90)
    tab_ref.movey(y_tab_center)

    # 3. Create and place the four prongs on top.
    for x_pos in x_positions:
        # Tapered base of the prong
        prong_taper = gf.components.taper(
            length=prong_taper_height,
            width1=prong_base_width,
            width2=prong_tip_width,
        )
        taper_ref = tmp << prong_taper
        taper_ref.rotate(90)
        taper_ref.move((x_pos, y_prongs_base))

        # Straight tip of the prong
        prong_straight = gf.components.rectangle(
            size=(prong_tip_width, prong_straight_height), centered=True
        )
        straight_ref = tmp << prong_straight
        straight_ref.move(
            (x_pos, y_prongs_base + prong_taper_height + prong_straight_height / 2.0)
        )

    # 4. Perform a boolean 'OR' operation.
    # FIX: Instead of trying to access the non-existent '.references' attribute,
    # we merge all shapes within the 'tmp' component by performing a boolean OR
    # of the component with itself. This is a standard method to create a union.
    final_device = gf.boolean(A=tmp, B=tmp, operation="or", layer=(1, 0))

    return final_device


# Instantiate the component to have a callable object.
# When this script is run, 'c' will hold the gdsfactory component.
c = create_device()