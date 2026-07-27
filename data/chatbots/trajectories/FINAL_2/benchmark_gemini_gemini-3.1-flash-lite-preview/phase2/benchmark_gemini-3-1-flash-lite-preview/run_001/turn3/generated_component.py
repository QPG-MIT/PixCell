import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Creates a unified geometry by performing a Boolean OR union 
    of a central rectangle and 5 taper pillars.
    """
    c = gf.Component()

    # 1. Define the main body (25 x 10)
    # Using the specified footprint
    body = gf.components.rectangle(size=(25, 10), centered=True, layer=(1, 0))

    # 2. Define the pillar primitive
    # Adjusted dimensions: length=4, base width=2, tip width=1
    taper_len = 4
    taper_shape = gf.components.taper(length=taper_len, width1=2.0, width2=1.0, layer=(1, 0))

    # We will accumulate the unified geometry here
    unified_geo = body

    # 3. Process Pillars
    # Helper to calculate position: 
    # To place the base on the edge (y=5 or y=-5), we shift the center of the taper 
    # by half the length (2.0)
    
    # Top pillars (4 pillars)
    top_positions = [-9, -3, 3, 9]
    for x in top_positions:
        temp_c = gf.Component()
        ref = temp_c << taper_shape
        ref.rotate(90)
        # Place center at (x, 5 + 2) so the base sits at y=5
        ref.move((x, 5 + 2)) 
        unified_geo = gf.boolean(unified_geo, temp_c, operation="or", layer=(1, 0))

    # Bottom pillar (1 pillar)
    temp_bottom = gf.Component()
    ref_bottom = temp_bottom << taper_shape
    ref_bottom.rotate(-90)
    # Place center at (0, -5 - 2) so the base sits at y=-5
    ref_bottom.move((0, -5 - 2))
    unified_geo = gf.boolean(unified_geo, temp_bottom, operation="or", layer=(1, 0))

    # 4. Add the resulting single polygon to our main component
    c << unified_geo

    return c

# Generate the component
device = custom_device()
device.write_gds("unified_device_v2.gds")

print("Successfully generated unified_device_v2.gds with improved geometry.")