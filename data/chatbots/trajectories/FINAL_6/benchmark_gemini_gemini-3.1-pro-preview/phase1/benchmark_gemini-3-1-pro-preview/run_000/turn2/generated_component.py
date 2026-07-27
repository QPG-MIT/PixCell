import gdsfactory as gf

@gf.cell
def star_coupler_refined(
    footprint: float = 4.7,
    wg_width: float = 0.15,
    petal_cx: float = 0.85,  # Offset from origin to shift the "belly" outwards
    petal_rx: float = 1.05,  # Length of the ellipse
    petal_ry: float = 0.45,  # Max width of the ellipse petal
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates the pinched star geometry using shifted overlapping ellipses.
    """
    c = gf.Component()

    # 1. Base cross (Ensures the 4.7um footprint and the straight thin tips)
    cross_comp = gf.components.cross(
        length=footprint, 
        width=wg_width, 
        layer=layer
    )

    # 2. Base ellipse shapes for the petals
    ellipse_h = gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    ellipse_v = gf.components.ellipse(radii=(petal_ry, petal_rx), layer=layer)

    # 3. Create Horizontal Dumbbell (Two shifted horizontal ellipses)
    h_right = gf.Component()
    h_right.add_ref(ellipse_h).movex(petal_cx)
    
    h_left = gf.Component()
    h_left.add_ref(ellipse_h).movex(-petal_cx)
    
    arm_h = gf.boolean(A=h_right, B=h_left, operation="or", layer=layer)

    # 4. Create Vertical Dumbbell (Two shifted vertical ellipses)
    v_top = gf.Component()
    v_top.add_ref(ellipse_v).movey(petal_cx)
    
    v_bottom = gf.Component()
    v_bottom.add_ref(ellipse_v).movey(-petal_cx)
    
    arm_v = gf.boolean(A=v_top, B=v_bottom, operation="or", layer=layer)

    # 5. Fuse the horizontal and vertical arms (This creates the pinched center)
    petals_combined = gf.boolean(A=arm_h, B=arm_v, operation="or", layer=layer)

    # 6. Final Fusion: Add the thin straight cross for the waveguide extensions
    final_geometry = gf.boolean(A=petals_combined, B=cross_comp, operation="or", layer=layer)

    # Add the final geometry polygon to the component
    c << final_geometry

    # Recover the routing ports from the original cross
    c.add_ports(cross_comp.ports)

    return c

if __name__ == "__main__":
    device = star_coupler_refined()
    device.show()