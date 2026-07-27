import gdsfactory as gf

@gf.cell
def pinched_petal_device() -> gf.Component:
    """
    Creates a four-leaf clover geometry with a pinched center
    and straight rectangular extensions at the tips.
    """
    c = gf.Component("pinched_petal_device")
    
    # ---------------------------------------------------------
    # Parametric Dimensions
    # ---------------------------------------------------------
    total_footprint = 4.7
    
    # Petal primitive dimensions (a single "football" shape)
    # We use ellipses shifted away from the center to create the pinch
    rx = 1.0   # Half-length of a single petal
    ry = 0.6   # Half-width of a single petal
    
    # The shift determines the central pinch. 
    # By shifting by slightly less than 'rx' (0.98 vs 1.0), the 
    # petals overlap just enough at (0,0) to merge into a single solid 
    # polygon with sharp 90-degree inner valleys.
    shift = 0.98 
    
    # Straight tip dimensions
    tip_width = 0.12 
    
    # ---------------------------------------------------------
    # Primitive Construction & Shifting
    # ---------------------------------------------------------
    # Base shapes
    ellipse_h = gf.components.ellipse(radii=(rx, ry), layer=(1, 0))
    ellipse_v = gf.components.ellipse(radii=(ry, rx), layer=(1, 0))
    cross_tips = gf.components.cross(length=total_footprint, width=tip_width, layer=(1, 0))
    
    # Create temporary components for each shifted petal so we can Boolean them
    petal_right = gf.Component()
    petal_right.add_ref(ellipse_h).movex(shift)
    
    petal_left = gf.Component()
    petal_left.add_ref(ellipse_h).movex(-shift)
    
    petal_top = gf.Component()
    petal_top.add_ref(ellipse_v).movey(shift)
    
    petal_bottom = gf.Component()
    petal_bottom.add_ref(ellipse_v).movey(-shift)
    
    # ---------------------------------------------------------
    # Composition via Boolean Operations
    # ---------------------------------------------------------
    # Union the horizontal petals
    h_petals = gf.boolean(petal_right, petal_left, operation="or", layer=(1, 0))
    
    # Union the vertical petals
    v_petals = gf.boolean(petal_top, petal_bottom, operation="or", layer=(1, 0))
    
    # Union all petals to form the central clover
    clover_core = gf.boolean(h_petals, v_petals, operation="or", layer=(1, 0))
    
    # Union the clover core with the straight cross tips
    final_geometry = gf.boolean(clover_core, cross_tips, operation="or", layer=(1, 0))
    
    # Add the final geometry to our main component
    c << final_geometry
    
    return c


if __name__ == "__main__":
    # Create the component
    device = pinched_petal_device()
    
    # Save the output to a GDS file
    device.write_gds("pinched_petal_device.gds")