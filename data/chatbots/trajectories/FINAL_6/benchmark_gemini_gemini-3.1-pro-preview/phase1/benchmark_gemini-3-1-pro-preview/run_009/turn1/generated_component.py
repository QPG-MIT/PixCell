import gdsfactory as gf

@gf.cell
def clover_mode_shape() -> gf.Component:
    """
    Creates the clover-like geometry using boolean operations on 
    standard parametric primitives (cross and ellipses).
    """
    c = gf.Component("clover_mode_shape")
    
    # Target Constraints & Proportions
    footprint = 4.7
    tip_width = 0.25        # Width of the straight narrow segments at the ends
    r_major = 1.85          # Semi-major axis of the elliptical bulges
    r_minor = 0.7           # Semi-minor axis (thickness) of the elliptical bulges
    layer = (1, 0)

    # 1. Base Primitives
    # The cross defines the full extent [4.7, 4.7] and straight tips
    cross = gf.components.cross(length=footprint, width=tip_width, layer=layer)
    
    # The ellipses define the curved, bulbous central profiles
    ellipse_h = gf.components.ellipse(radii=(r_major, r_minor), layer=layer)
    ellipse_v = gf.components.ellipse(radii=(r_minor, r_major), layer=layer)

    # 2. Boolean Assembly
    # First, union the two ellipses together
    ellipses_union = gf.boolean(
        A=ellipse_h, 
        B=ellipse_v, 
        operation="or", 
        layer=layer
    )
    
    # Next, union the resulting shape with the cross to add the straight tips
    final_geometry = gf.boolean(
        A=ellipses_union, 
        B=cross, 
        operation="or", 
        layer=layer
    )

    # Add the unified structure to the main component
    c << final_geometry

    return c

if __name__ == "__main__":
    # Create the component
    c = clover_mode_shape()
    
    # Explicitly write the GDS file
    c.write_gds("output.gds")