import gdsfactory as gf

@gf.cell
def create_new_device():
    """
    Creates the new target shape with non-uniform petals using a
    boolean union of two different ellipses and four square stems.
    """
    target_layer = (1, 0)

    # 1. Define parameters based on visual estimation of the new target image.
    # The vertical petals are taller and narrower, defined by ellipse_v.
    # The horizontal petals are wider and shorter, defined by ellipse_h.
    
    # Radii for the tall vertical ellipse (radius_x, radius_y)
    ellipse_v_radii = (1.6, 2.1)
    
    # Radii for the wide horizontal ellipse (radius_x, radius_y)
    ellipse_h_radii = (2.0, 1.5)
    
    # Dimensions for the square stems
    stem_size = 0.25

    # 2. Create the primitive components
    
    # Tall ellipse for the vertical arms/petals
    ellipse_v = gf.components.ellipse(radii=ellipse_v_radii, layer=target_layer)
    
    # Wide ellipse for the horizontal arms/petals
    ellipse_h = gf.components.ellipse(radii=ellipse_h_radii, layer=target_layer)
    
    # Square stem
    stem = gf.components.rectangle(size=(stem_size, stem_size), layer=target_layer)

    # 3. Create the main component for assembly
    c = gf.Component("asymmetric_petal_cross")

    # 4. Create the base body by taking the union of the two different ellipses
    base_body = gf.boolean(A=ellipse_v, B=ellipse_h, operation="or", layer=target_layer)
    c.add_ref(base_body)

    # 5. Add and position the four stems at the extremities
    # The position of each stem is based on the major radius of its corresponding ellipse.
    y_major_radius = ellipse_v_radii[1]  # The 'y' radius of the vertical ellipse
    x_major_radius = ellipse_h_radii[0]  # The 'x' radius of the horizontal ellipse

    # Top stem
    s_top = c << stem
    s_top.movey(y_major_radius + stem_size / 2)

    # Bottom stem
    s_bottom = c << stem
    s_bottom.movey(-(y_major_radius + stem_size / 2))

    # Right stem
    s_right = c << stem
    s_right.movex(x_major_radius + stem_size / 2)
    
    # Left stem
    s_left = c << stem
    s_left.movex(-(x_major_radius + stem_size / 2))
    
    # 6. Flatten the component to merge all shapes into a single, unified polygon
    c.flatten()

    return c

# Instantiate the component
device = create_new_device()

# Write the component to a GDS file for output
device.write_gds("device.gds")

# Optional: You can uncomment the line below to show the GDS in a viewer
# device.show()