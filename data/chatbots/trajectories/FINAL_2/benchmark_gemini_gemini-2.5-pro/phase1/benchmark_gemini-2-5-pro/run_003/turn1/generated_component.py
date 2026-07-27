import gdsfactory as gf

@gf.cell
def create_device():
    """
    Recreates the specified geometry by composing parametric primitives
    and performing a boolean union. This version uses the correct syntax for the move() method.
    """
    # Create a temporary component to hold the constituent shapes
    c = gf.Component("temp_assembly")

    # --- 1. Define Geometric Parameters ---
    # Derived from the 25x10 um footprint and image proportions
    body_width = 25.0
    body_height = 5.0
    body_ymin = 1.0

    bottom_taper_height = 1.0
    bottom_taper_width_top = 3.0
    bottom_taper_width_bottom = 1.5

    prong_taper_height = 2.0
    prong_straight_height = 2.0
    prong_base_width = 4.0
    prong_top_width = 1.5

    num_prongs = 4
    prong_gap = 3.0  # (25 - 4 * 4) / 3 = 3

    # --- 2. Create and Place Primitive Shapes ---

    # Main Body
    # Primitives are centered at (0,0) by default. Move it to the correct position.
    body = c << gf.components.rectangle(size=(body_width, body_height))
    # Move the reference by a vector equal to its target center coordinate
    body.move((0, body_ymin + body_height / 2.0))

    # Bottom Taper (rotated vertical)
    # The default taper is horizontal. length -> height, width1/2 -> bottom/top widths
    bottom_taper = gf.components.taper(
        length=bottom_taper_height,
        width1=bottom_taper_width_bottom,
        width2=bottom_taper_width_top,
    )
    b_taper_ref = c << bottom_taper
    b_taper_ref.rotate(90)
    # Move the reference by a vector equal to its target center coordinate
    b_taper_ref.move((0, bottom_taper_height / 2.0))

    # Top Prongs
    prong_pitch = prong_base_width + prong_gap
    start_x = -(num_prongs - 1) * prong_pitch / 2.0
    prong_x_centers = [start_x + i * prong_pitch for i in range(num_prongs)]
    prong_ymin = body_ymin + body_height

    for x_center in prong_x_centers:
        # Tapered base of the prong (rotated vertical)
        prong_taper = gf.components.taper(
            length=prong_taper_height,
            width1=prong_base_width,
            width2=prong_top_width,
        )
        pt_ref = c << prong_taper
        pt_ref.rotate(90)
        pt_ref.move((x_center, prong_ymin + prong_taper_height / 2.0))

        # Straight top part of the prong
        prong_straight = gf.components.rectangle(
            size=(prong_top_width, prong_straight_height)
        )
        ps_ref = c << prong_straight
        ps_ref.move((x_center, prong_ymin + prong_taper_height + prong_straight_height / 2.0))

    # --- 3. Perform Boolean Union ---
    # Flatten the component to convert references to polygons
    # Then merge all polygons on the same layer into a single shape
    final_device = gf.geometry.union(c, by_layer=True)
    final_device.name = "final_device"

    return final_device

# Instantiate and display the component
if __name__ == "__main__":
    device = create_device()
    device.show()