import gdsfactory as gf

@gf.cell
def petal_device():
    """
    Recreates the 4-petal geometry with stubs at the ends.
    Footprint: 4.7um x 4.7um
    """
    # Dimensions based on visual analysis and constraints
    total_span = 4.7
    stub_width = 0.35
    # Petals are slightly shorter than the span to reveal the stubs
    petal_total_length = 4.1 
    petal_max_width = 1.3
    layer = (1, 0)

    # 1. Create the base cross
    # This ensures the total footprint is exactly 4.7um and provides the end stubs.
    stubs = gf.components.cross(length=total_span, width=stub_width, layer=layer)

    # 2. Create the horizontal petals (single ellipse centered at 0,0)
    # radii=(x_radius, y_radius)
    horiz_petals = gf.components.ellipse(
        radii=(petal_total_length / 2, petal_max_width / 2), 
        layer=layer
    )

    # 3. Create the vertical petals
    vert_petals = gf.components.ellipse(
        radii=(petal_max_width / 2, petal_total_length / 2), 
        layer=layer
    )

    # 4. Perform Boolean operations to combine all parts into a single solid geometry
    # First, join the horizontal and vertical ellipses
    petals_union = gf.boolean(
        A=horiz_petals, 
        B=vert_petals, 
        operation="or", 
        layer=layer
    )
    
    # Then, join that result with the cross structure
    # This creates the final unioned geometry with the stubs at the tips.
    final_device = gf.boolean(
        A=petals_union, 
        B=stubs, 
        operation="or", 
        layer=layer
    )

    return final_device

if __name__ == "__main__":
    # Generate the component
    c = petal_device()
    
    # Show in layout viewer
    c.show()
    
    # Print dimensions using properties to avoid subscripting errors
    # xsize and ysize are the most robust ways to check footprints in GDSFactory
    print(f"Device Footprint: {c.xsize:.2f} um x {c.ysize:.2f} um")