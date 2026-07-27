import gdsfactory as gf

@gf.cell
def create_prong(
    taper_length: float = 2.5,
    straight_length: float = 1.5,
    taper_width_base: float = 4.0,
    straight_width: float = 1.5,
) -> gf.Component:
    """
    Creates a single vertical prong sub-component with a tapered base.
    The component origin (0,0) is at the center of its base.
    """
    prong = gf.Component("prong")

    # Create the tapered base, oriented vertically
    taper = gf.components.taper(
        length=taper_length, width1=taper_width_base, width2=straight_width
    )
    taper_ref = prong << taper
    taper_ref.rotate(90)
    taper_ref.ymin = 0
    taper_ref.x = 0

    # Create the straight section and place it on top of the taper
    straight_ref = prong << gf.components.rectangle(
        size=(straight_width, straight_length)
    )
    straight_ref.ymin = taper_ref.ymax
    straight_ref.x = 0
    
    return prong


@gf.cell
def create_four_prong_device() -> gf.Component:
    """
    Creates the final device by assembling primitives and performing a boolean union.
    The geometry is based on the provided image and footprint.
    """
    # --- 1. Define Dimensions ---
    # Based on footprint [25, 10] and visual inspection
    body_width = 25.0
    body_height = 5.0
    
    # Prong dimensions (total prong height = 2.5 + 1.5 = 4.0)
    prong_taper_length = 2.5
    prong_straight_length = 1.5
    prong_taper_width_base = 4.0
    prong_straight_width = 1.5

    # Tab dimensions (total height = 1.0 + 5.0 + 4.0 = 10.0)
    bottom_tab_length = 1.0
    bottom_tab_width_top = 3.0
    bottom_tab_width_bottom = 1.5

    # Layout parameters for prong placement
    num_prongs = 4
    prong_spacing = 6.0

    # --- 2. Assemble Parts in a Container ---
    # A temporary component to hold all shapes before the final union
    parts_container = gf.Component("parts_for_union")

    # Main rectangular body, centered at the origin
    body = gf.components.rectangle(size=(body_width, body_height))
    body_ref = parts_container << body
    body_ref.center = (0, 0)

    # Bottom tapered tab
    bottom_tab = gf.components.taper(
        length=bottom_tab_length,
        width1=bottom_tab_width_top,
        width2=bottom_tab_width_bottom,
    )
    tab_ref = parts_container << bottom_tab
    tab_ref.rotate(-90)  # Rotate to point downwards
    
    # Manually align the tab by coordinates
    tab_ref.x = body_ref.center[0]
    tab_ref.ymax = body_ref.ymin

    # Create and place the four top prongs
    prong_component = create_prong(
        taper_length=prong_taper_length,
        straight_length=prong_straight_length,
        taper_width_base=prong_taper_width_base,
        straight_width=prong_straight_width,
    )
    
    start_x = - (num_prongs - 1) * prong_spacing / 2
    for i in range(num_prongs):
        x_pos = start_x + i * prong_spacing
        p_ref = parts_container << prong_component
        p_ref.x = x_pos
        # Place the base of the prong on the top edge of the body
        p_ref.ymin = body_ref.ymax

    # --- 3. Create Final Monolithic Shape ---
    # ** FIX STARTS HERE **
    # Perform a boolean union on all placed parts to merge them into a single polygon.
    # The `union` function is in the top-level `gf` module, not `gf.geometry`.
    final_device = gf.union(parts_container, by_layer=True)
    # ** FIX ENDS HERE **
    
    return final_device


if __name__ == "__main__":
    # Instantiate the final device
    device = create_four_prong_device()
    
    # Optional: Display the component in a viewer
    device.show()
    
    # Optional: Save the component to a GDS file
    # device.write_gds("four_prong_device.gds")