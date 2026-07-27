import gdsfactory as gf
import gdsfactory.functions as gf_f # Import gdsfactory.functions, aliased as gf_f

@gf.cell
def complex_cross_from_primitives():
    """
    Recreates a complex cross geometry with curved lobes and straight stems
    using GDSFactory parametric primitives and boolean operations.
    The design aims for a 4.7um x 4.7um footprint.
    """
    c = gf.Component("complex_cross")
    layer = (1, 0) # Use default layer

    # 1. Define parameters for the central rounded "bulge" part
    # L_base_cross: Overall length/width of the initial cross shape.
    # W_base_cross_arm: Width of the arms of the initial cross.
    # offset_dist: Distance to offset, creating the curved bulge and rounding corners.
    base_cross_length = 2.5  # Defines the core span of the cross
    base_cross_arm_width = 0.2 # Thickness of the lines forming the base cross
    offset_distance = 0.45 # Expands the base cross to create the curved lobes

    # Create the base cross component
    # gf.components.cross is centered by default, so 'centered' argument is not needed.
    base_cross_comp = gf.components.cross(
        length=base_cross_length,
        width=base_cross_arm_width,
        layer=layer,
    )

    # Apply the offset operation to create the rounded, bulging part
    # Corrected: Use gf_f.offset instead of gf.geometry.offset
    rounded_bulge_comp = gf_f.offset(
        base_cross_comp,
        distance=offset_distance,
        layer=layer
    )
    # Add this component to our main component 'c' as a reference
    rounded_ref = c << rounded_bulge_comp

    # 2. Define parameters for the straight "stem" parts
    stem_width = 0.3     # Width of the straight stem
    stem_length = 0.65   # Length of the straight stem (adjusted for 4.7um total footprint)

    # Calculate the center coordinate for placing each stem
    # This is the distance from the origin (0,0) to the center of the stem.
    # First, find the outer edge of the rounded_bulge_comp:
    # (base_cross_length / 2 + offset_distance) = (2.5 / 2 + 0.45) = 1.25 + 0.45 = 1.7 um.
    # The stem's center will be at this coordinate plus half its length:
    stem_center_coord = (base_cross_length / 2 + offset_distance) + (stem_length / 2)
    # stem_center_coord = 1.7 + (0.65 / 2) = 1.7 + 0.325 = 2.025 um

    # Create the base stem components (one for vertical, one for horizontal)
    # The vertical stem is size=(W_stem, L_stem)
    stem_vertical_comp = gf.components.rectangle(
        size=(stem_width, stem_length),
        layer=layer,
        centered=True
    )
    # The horizontal stem is effectively size=(L_stem, W_stem)
    stem_horizontal_comp = gf.components.rectangle(
        size=(stem_length, stem_width), # Swapped dimensions for horizontal orientation
        layer=layer,
        centered=True
    )

    # Place the four stems as references to 'c'
    stem_north_ref = c << stem_vertical_comp
    stem_north_ref.move((0, stem_center_coord))

    stem_south_ref = c << stem_vertical_comp
    stem_south_ref.move((0, -stem_center_coord))

    stem_east_ref = c << stem_horizontal_comp
    stem_east_ref.move((stem_center_coord, 0))

    stem_west_ref = c << stem_horizontal_comp
    stem_west_ref.move((-stem_center_coord, 0))

    # 3. Perform a boolean union of all parts to create a single, continuous shape
    components_to_union = [
        rounded_ref,
        stem_north_ref,
        stem_south_ref,
        stem_east_ref,
        stem_west_ref
    ]

    # Create the final component by performing the boolean union
    # We add the result to 'c' directly, effectively making 'c' the final shape.
    # To keep the original references, we create a new component for the final shape.
    final_shape = gf.boolean(
        components_to_union,
        operation="or", # Union all geometries
        layer=layer
    )
    
    return final_shape

# Create the device and save it
if __name__ == "__main__":
    device = complex_cross_from_primitives()
    device.show() # To display the component visually (requires KLayout)
    # device.write_gds("complex_cross_device.gds") # Uncomment to save GDS
    print(f"Generated device: {device.name}")
    print(f"Device bounds: {device.get_bounding_box()}")
    # Expected bounds: [[-2.35, -2.35], [2.35, 2.35]], resulting in a 4.7x4.7um footprint.