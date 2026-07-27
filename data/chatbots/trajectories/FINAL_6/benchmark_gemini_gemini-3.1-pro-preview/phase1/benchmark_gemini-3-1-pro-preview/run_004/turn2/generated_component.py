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
    # Thicked slightly to 0.25 to better match the visual weight of the target image.
    base_cross = gf.components.cross(
        length=4.7, 
        width=0.25, 
        layer=(1, 0)
    )

    # 2. Shifted Petals (The key to the pinched center)
    # We create a compound component of 4 displaced ellipses. 
    # By shifting them OUTWARDS from the center, they taper as they approach the origin,
    # creating the deep concave V-notches at the 45-degree diagonals.
    petals = gf.Component("petals")
    
    # Base ellipse for the petals (rx is length-wise, ry is width-wise)
    ell_h = gf.components.ellipse(radii=(1.0, 0.45), layer=(1, 0))
    ell_v = gf.components.ellipse(radii=(0.45, 1.0), layer=(1, 0))
    
    # Add and shift horizontal petals
    # Shifting by 0.95um means they span roughly from x=-0.05 to x=1.95
    # This leaves exactly 0.4um for the straight rectangular tip (2.35 - 1.95)
    petals.add_ref(ell_h).movex(0.95)   # Right petal
    petals.add_ref(ell_h).movex(-0.95)  # Left petal
    
    # Add and shift vertical petals
    petals.add_ref(ell_v).movey(0.95)   # Top petal
    petals.add_ref(ell_v).movey(-0.95)  # Bottom petal

    # 3. Boolean Assembly
    # Merge the cross and the 4 petals into a single continuous polygon.
    final_shape = gf.boolean(base_cross, petals, operation="or", layer=(1, 0))

    # Add the unified shape to our main component
    c << final_shape

    return c

if __name__ == "__main__":
    # Create the component
    device = star_device()
    
    # Write to GDS file
    device.write_gds("star_device.gds")