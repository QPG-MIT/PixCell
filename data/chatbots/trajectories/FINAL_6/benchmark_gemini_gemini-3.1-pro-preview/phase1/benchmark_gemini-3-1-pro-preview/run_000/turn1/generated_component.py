import gdsfactory as gf

@gf.cell
def star_coupler(
    footprint: float = 4.7,
    wg_width: float = 0.2,
    petal_length: float = 3.8,
    petal_width: float = 1.1,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates the star geometry using parametric primitives and boolean operations.
    
    Args:
        footprint: Total length/width of the device (4.7um constraint).
        wg_width: The width of the straight waveguide extensions.
        petal_length: The length of the elliptical bloated sections.
        petal_width: The maximum width of the elliptical petals.
        layer: Target GDS layer.
    """
    c = gf.Component()

    # 1. Base extensions (The thin straight ends forming a 4.7um bounding box)
    straight_cross = gf.components.cross(
        length=footprint, 
        width=wg_width, 
        layer=layer
    )

    # 2. The central petals (Orthogonal intersecting ellipses)
    ellipse_h = gf.components.ellipse(
        radii=(petal_length / 2, petal_width / 2), 
        layer=layer
    )
    
    ellipse_v = gf.components.ellipse(
        radii=(petal_width / 2, petal_length / 2), 
        layer=layer
    )

    # 3. Boolean Operations to fuse the shapes
    # First, combine the two ellipses to create the 4-petal core with sharp inner corners
    star_core = gf.boolean(
        A=ellipse_h, 
        B=ellipse_v, 
        operation="or", 
        layer=layer
    )

    # Second, merge the core with the straight cross extensions
    final_geometry = gf.boolean(
        A=star_core, 
        B=straight_cross, 
        operation="or", 
        layer=layer
    )

    # Add the single merged polygon to our component
    c << final_geometry

    # Optional but recommended: 
    # Boolean operations strip port metadata. Since the extremities align 
    # perfectly with the original cross, we can safely copy its ports.
    c.add_ports(straight_cross.ports)

    return c

if __name__ == "__main__":
    # Generate and display the device
    device = star_coupler()
    device.show()