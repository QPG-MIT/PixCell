import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def my_stylized_cross(
    petal_radius: float = 2.0,
    stub_length: float = 1.0,
    stub_width: float = 1.0,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Create a stylized cross using GDSFactory parametric functions, resembling a four-petal flower.

    Args:
        petal_radius: Radius of the circular "petals."
        stub_length: Length of the rectangular stubs at the ends of the cross.
        stub_width: Width of the rectangular stubs.
        layer: GDS layer for the cross.

    Returns:
        A GDSFactory component representing the stylized cross.
    """
    c = gf.Component("stylized_cross")

    # Create the petals (circles)
    petal_top = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_bottom = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_left = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_right = c << gf.components.circle(radius=petal_radius, layer=layer)

    petal_top.movey(petal_radius)
    petal_bottom.movey(-petal_radius)
    petal_left.movex(-petal_radius)
    petal_right.movex(petal_radius)

    # Create the rectangular stubs
    stub_top = c << gf.components.rectangle(size=(stub_width, stub_length), layer=layer, centered=True)
    stub_bottom = c << gf.components.rectangle(size=(stub_width, stub_length), layer=layer, centered=True)
    stub_left = c << gf.components.rectangle(size=(stub_length, stub_width), layer=layer, centered=True)
    stub_right = c << gf.components.rectangle(size=(stub_length, stub_width), layer=layer, centered=True)

    stub_top.movey(2 * petal_radius + stub_length / 2)
    stub_bottom.movey(-(2 * petal_radius + stub_length / 2))
    stub_left.movex(-(2 * petal_radius + stub_length / 2))
    stub_right.movex(2 * petal_radius + stub_length / 2)

    return c

if __name__ == "__main__":
    c = my_stylized_cross()
    c.show()
    c.write_gds("my_stylized_cross.gds")
    print(f"Device footprint: {c.bbox}")