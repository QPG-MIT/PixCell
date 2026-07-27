import gdsfactory as gf

@gf.cell
def crossing_star_coupler() -> gf.Component:
    """
    Creates the symmetric star-like crossing device shown in the target image.
    Uses two intersecting ellipses centered at the origin to form the main taper,
    and an underlying cross for the straight extremities.
    """
    # ------------------------------------------------------------------
    # 1. Dimensional Parameters
    # ------------------------------------------------------------------
    # The total bounding box is 4.7 x 4.7 um
    total_footprint = 4.7
    
    # Width of the thin, straight extremities
    straight_width = 0.20 
    
    # Ellipse parameters
    # The major radius is set to 1.9um. This means the ellipse ends just before 
    # the 2.35um edge, leaving ~0.45um of pure straight waveguide at each tip.
    radius_long = 1.9  
    
    # The minor radius controls the width at the center. 0.8um radius means 
    # the central intersection is 1.6um wide, creating the thick central bulge.
    radius_wide = 0.80 

    # ------------------------------------------------------------------
    # 2. Base Primitives
    # ------------------------------------------------------------------
    # Underlying cross that guarantees the exact 4.7um footprint
    base_cross = gf.components.cross(
        length=total_footprint, 
        width=straight_width, 
        layer=(1, 0)
    )

    # Ellipses for the tapered petals (centered at origin)
    ellipse_h = gf.components.ellipse(
        radii=(radius_long, radius_wide), 
        layer=(1, 0)
    )
    
    ellipse_v = gf.components.ellipse(
        radii=(radius_wide, radius_long), 
        layer=(1, 0)
    )

    # ------------------------------------------------------------------
    # 3. Boolean Construction
    # ------------------------------------------------------------------
    # Step 1: Fuse the horizontal and vertical ellipses into a single 4-pointed star bulge
    central_star = gf.boolean(
        A=ellipse_h,
        B=ellipse_v,
        operation="or",
        layer=(1, 0)
    )

    # Step 2: Fuse the central star with the underlying thin cross
    # The straight lines of the cross will smoothly "catch" the tips of the ellipses
    final_device = gf.boolean(
        A=central_star,
        B=base_cross,
        operation="or",
        layer=(1, 0)
    )

    return final_device


if __name__ == "__main__":
    # Generate the component
    c = crossing_star_coupler()
    
    # Write the output to a GDS file
    c.write_gds("crossing_star_coupler.gds")