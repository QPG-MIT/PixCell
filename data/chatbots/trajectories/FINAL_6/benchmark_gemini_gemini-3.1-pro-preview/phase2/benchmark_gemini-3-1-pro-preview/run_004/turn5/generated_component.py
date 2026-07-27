import gdsfactory as gf

@gf.cell
def star_device() -> gf.Component:
    """
    Creates a star-like geometry with four distinct bulging petals that pinch inwards 
    at the center, leaving straight rectangular tips at the ends.
    Footprint is strictly 4.7 x 4.7 um.
    """
    c = gf.Component("star_device")
    
    # 1. Base Cross
    # Provides the exact 4.7um footprint and the straight rectangular tips.
    base_cross = gf.components.cross(
        length=4.7, 
        width=0.22, 
        layer=(1, 0)
    )

    # 2. Shifted Petals 
    # CRITICAL FIX: To create a deep, sharp pinch at the center, the intersection
    # of the ellipses must be much closer to the origin. 
    # By setting shift_dist slightly larger than rx, we pull the ellipses outwards.
    # The parameters are mathematically tuned so that:
    # a) The ellipses intersect at a sharp point very close to the center (x ~ 0.16).
    # b) They still completely cover the central 0.22 width of the base cross 
    #    (their y-intercept is ~0.12, which is > 0.11 half-width).
    # c) They taper gracefully into the straight tips around x ~ 1.93.
    petals = gf.Component("petals")
    
    rx = 0.915
    ry = 0.55
    shift_dist = 1.035
    
    # Base ellipses for the petals
    ell_h = gf.components.ellipse(radii=(rx, ry), layer=(1, 0))
    ell_v = gf.components.ellipse(radii=(ry, rx), layer=(1, 0))
    
    # Add and shift horizontal petals
    petals.add_ref(ell_h).movex(shift_dist)   # Right petal
    petals.add_ref(ell_h).movex(-shift_dist)  # Left petal
    
    # Add and shift vertical petals
    petals.add_ref(ell_v).movey(shift_dist)   # Top petal
    petals.add_ref(ell_v).movey(-shift_dist)  # Bottom petal

    # 3. Boolean Assembly
    # Merge the cross and the 4 overlapping petals into a single continuous polygon.
    final_shape = gf.boolean(base_cross, petals, operation="or", layer=(1, 0))

    # Add the unified shape to our main component
    c << final_shape

    return c

if __name__ == "__main__":
    # Create the component
    device = star_device()
    
    # Write to GDS file
    device.write_gds("star_device.gds")