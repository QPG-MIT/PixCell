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
    # Provides the exact 4.7um footprint, the straight tips, and a solid central anchor.
    base_cross = gf.components.cross(
        length=4.7, 
        width=0.25, 
        layer=(1, 0)
    )

    # 2. Shifted Petals 
    # To create the deep concave notches seen in the target, we must carefully balance
    # the ellipse radius and its shift. 
    # By using a larger shift (1.05) and smaller radius (0.95), the ellipses barely 
    # overlap each other near the center, creating a very deep, sharp notch.
    petals = gf.Component("petals")
    
    rx = 0.95
    ry = 0.45
    shift_dist = 1.05
    
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
    # Merge the cross and the 4 petals into a single continuous polygon.
    # The cross will perfectly fill the tiny 0.1um gap left at the very center by the shifted petals.
    final_shape = gf.boolean(base_cross, petals, operation="or", layer=(1, 0))

    # Add the unified shape to our main component
    c << final_shape

    return c

if __name__ == "__main__":
    # Create the component
    device = star_device()
    
    # Write to GDS file
    device.write_gds("star_device.gds")