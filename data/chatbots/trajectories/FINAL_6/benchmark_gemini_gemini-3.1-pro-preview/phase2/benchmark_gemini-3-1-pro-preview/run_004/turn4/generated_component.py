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
    # Provides the exact 4.7um footprint and the straight tips.
    # The width is slightly reduced to match the proportions in the target.
    base_cross = gf.components.cross(
        length=4.7, 
        width=0.22, 
        layer=(1, 0)
    )

    # 2. Shifted Petals 
    # CRITICAL FIX: By ensuring shift_dist < rx, the ellipses overlap at the origin.
    # This overlap creates a smooth, deep V-notch from intersecting curves, completely 
    # covering the central part of the cross to avoid a flat-bottomed notch.
    petals = gf.Component("petals")
    
    rx = 1.05
    ry = 0.45
    shift_dist = 1.0
    
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