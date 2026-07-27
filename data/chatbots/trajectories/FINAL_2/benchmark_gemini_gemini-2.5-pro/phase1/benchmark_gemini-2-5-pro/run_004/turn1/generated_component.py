import gdsfactory as gf
import gdsfactory.typings as gt


@gf.cell
def create_prong_unit(
    taper_height: float = 2.0,
    straight_height: float = 2.0,
    base_width: float = 4.0,
    top_width: float = 2.0,
    layer: gt.LayerSpec = (1, 0),
) -> gf.Component:
    """Creates a single vertical prong unit with a tapered base.

    The component is built such that its bottom-center is at (0, 0).

    Args:
        taper_height: Height of the tapered section.
        straight_height: Height of the top straight section.
        base_width: Width at the bottom of the taper.
        top_width: Width of the top straight section and top of the taper.
        layer: GDS layer for the geometry.
    """
    prong = gf.Component()

    # Create the tapered and straight sections
    taper = gf.components.taper(
        length=taper_height,
        width1=base_width,
        width2=top_width,
        layer=layer,
    )
    straight = gf.components.rectangle(
        size=(top_width, straight_height), layer=layer
    )

    # Add sections as references and stack them vertically
    taper_ref = prong << taper
    straight_ref = prong << straight
    
    # Position straight part on top of the taper
    straight_ref.connect("o1", taper_ref.ports["o2"])

    # Normalize the component's position: center it horizontally and set its base to y=0
    prong.movex(-prong.center[0])
    prong.movey(-prong.ymin)
    
    return prong


@gf.cell
def create_device() -> gf.Component:
    """
    Recreates the device from the image using parametric gdsfactory components.

    The device consists of a central rectangular body, four prongs on top,
    and a single tapered pin at the bottom, all merged into a single shape.
    The final component matches the specified footprint of 25x10 um.
    """
    # --- Define Device Dimensions ---
    # Based on footprint [25, 10] and visual proportions
    rect_width = 25.0
    rect_height = 5.0
    prong_taper_height = 2.0
    prong_straight_height = 2.0
    prong_base_width = 4.0
    prong_top_width = 2.0
    prong_pitch = 6.0
    bottom_taper_height = 1.0
    bottom_taper_top_width = 4.0
    bottom_taper_bottom_width = 2.0
    layer = (1, 0)

    # --- Create a temporary component to hold the parts before merging ---
    parts = gf.Component("parts_to_merge")

    # --- 1. Create and place the main rectangular body ---
    main_body = gf.components.rectangle(
        size=(rect_width, rect_height), layer=layer
    )
    body_ref = parts << main_body
    # Position the body. Using the direct .center property on the reference.
    body_ref.center = (0, -1.5)

    # --- 2. Create and place the array of top prongs ---
    prong_unit = create_prong_unit(
        taper_height=prong_taper_height,
        straight_height=prong_straight_height,
        base_width=prong_base_width,
        top_width=prong_top_width,
        layer=layer,
    )
    prongs_array = parts.add_array(
        component=prong_unit, columns=4, rows=1, spacing=(prong_pitch, 0)
    )
    # Center the array horizontally and place its base on top of the main body.
    prongs_array.center = (0, prongs_array.center[1]) 
    prongs_array.ymin = body_ref.ymax

    # --- 3. Create and place the bottom taper ---
    bottom_taper = gf.components.taper(
        length=bottom_taper_height,
        width1=bottom_taper_top_width,
        width2=bottom_taper_bottom_width,
        layer=layer,
    )
    bottom_taper_ref = parts << bottom_taper
    # Rotate and align the top of the taper with the bottom of the main body.
    bottom_taper_ref.rotate(90)
    bottom_taper_ref.center = (0, bottom_taper_ref.center[1])
    bottom_taper_ref.ymax = body_ref.ymin

    # --- 4. Perform a union operation to merge all parts into a single polygon ---
    final_device = gf.geometry.union(parts, by_layer=True, layer=layer)
    final_device.name = "final_device"

    return final_device

# --- Main execution block ---
if __name__ == "__main__":
    # 1. Create an instance of the device
    device = create_device()

    # 2. Show the device in a GDS viewer (optional, but good for verification)
    device.show()

    # 3. Write the component to a GDS file
    device.write_gds("output.gds")