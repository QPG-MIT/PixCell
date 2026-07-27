import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def my_stylized_cross(
    petal_radius: float = 2.0,
    stub_length: float = 0.5,
    stub_width: float = 0.7,
    layer: LayerSpec = (1, 0),
    petal_distance_from_origin: float = 1.5
) -> gf.Component:
    """
    Create a stylized cross using GDSFactory parametric functions, resembling a four-petal flower.

    Args:
        petal_radius: Radius of the circular "petals."
        stub_length: Length of the rectangular stubs at the ends of the cross.
        stub_width: Width of the rectangular stubs.
        layer: GDS layer for the cross.
        petal_distance_from_origin: how far from the origin the petals are moved.

    Returns:
        A GDSFactory component representing the stylized cross.
    """
    c = gf.Component("stylized_cross")

    # Create the petals (circles)
    petal_top = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_bottom = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_left = c << gf.components.circle(radius=petal_radius, layer=layer)
    petal_right = c << gf.components.circle(radius=petal_radius, layer=layer)

    petal_top.movey(petal_distance_from_origin)
    petal_bottom.movey(-petal_distance_from_origin)
    petal_left.movex(-petal_distance_from_origin)
    petal_right.movex(petal_distance_from_origin)

    # Create the rectangular stubs
    stub_top = c << gf.components.rectangle(size=(stub_width, stub_length), layer=layer, centered=True)
    stub_bottom = c << gf.components.rectangle(size=(stub_width, stub_length), layer=layer, centered=True)
    stub_left = c << gf.components.rectangle(size=(stub_length, stub_width), layer=layer, centered=True)
    stub_right = c << gf.components.rectangle(size=(stub_length, stub_width), layer=layer, centered=True)

    stub_top.movey(2 * petal_radius - petal_radius / 4.0)  # brings stub closer to center
    stub_bottom.movey(-(2 * petal_radius - petal_radius / 4.0))  # brings stub closer to center
    stub_left.movex(-(2 * petal_radius - petal_radius / 4.0)) # brings stub closer to center
    stub_right.movex(2 * petal_radius - petal_radius / 4.0) # brings stub closer to center

    return c

if __name__ == "__main__":
    c = my_stylized_cross()
    c.show()
    c.write_gds("my_stylized_cross.gds")
    print(f"Device footprint: {c.bbox}")