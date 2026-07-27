import gdsfactory as gf

@gf.cell
def device():
    """Creates a four-petal cross shape based on the provided image.

    This version corrects a runtime error by avoiding in-place modification
    of cached components. It correctly uses component references for transformation
    before performing a boolean operation.
    """

    # 1. Define Dimensions based on the 4.7x4.7 um footprint
    device_size = 4.7
    arm_length = device_size / 2.0  # Length from center to tip

    # Apportion the arm length between the petal body (ellipse) and the stem (rectangle).
    # These proportions are estimated from the visual appearance in the image.
    stem_length = 0.35
    stem_width = 0.30
    ellipse_major_radius = arm_length - stem_length      # => 2.35 - 0.35 = 2.0
    ellipse_minor_radius = 0.65                          # Estimated for petal width

    # 2. Create the base primitive components. These are treated as immutable templates.
    body_primitive = gf.components.ellipse(radii=(ellipse_minor_radius, ellipse_major_radius))
    stem_primitive = gf.components.rectangle(size=(stem_width, stem_length))

    # 3. FIX: Create a new temporary component to correctly position the stem.
    # Instead of modifying the cached `stem_primitive` in-place (which causes the error),
    # we add a *reference* to it in a new component and move the *reference*.
    positioned_stem = gf.Component("positioned_stem_temp")
    stem_ref = positioned_stem << stem_primitive
    stem_ref.movey(ellipse_major_radius + stem_length / 2.0)

    # 4. Create the final "petal unit" by performing a boolean union.
    # The boolean operation takes the geometry from the body primitive and the
    # geometry from the new component containing the correctly moved stem.
    petal_unit = gf.boolean(
        A=body_primitive, B=positioned_stem, operation="or"
    )

    # 5. Assemble the final device by rotating references to the petal unit
    c = gf.Component("petal_cross")

    # Add four references to the petal_unit component
    ref0 = c << petal_unit
    ref90 = c << petal_unit
    ref180 = c << petal_unit
    ref270 = c << petal_unit

    # Rotate three of the references to form the four-fold symmetric cross
    ref90.rotate(90)
    ref180.rotate(180)
    ref270.rotate(270)
    
    return c

# Instantiate the component and write it to a GDS file.
if __name__ == "__main__":
    my_device = device()
    my_device.write_gds("output.gds")