import gdsfactory as gf
from gdsfactory import Component
from gdsfactory.geometry.boolean import boolean


@gf.cell
def my_device() -> Component:
    """Recreates the device from the provided image using GDSFactory parametric functions."""
    c = gf.Component("my_device")

    # Define key parameters based on the image
    base_width = 20  # approximate width of the main rectangle
    base_height = 7 # approximate height of the main rectangle
    connector_width = 2
    connector_height = 2 # approximate
    pillar_bottom_width = 3  # Width at the base of the pillar
    pillar_top_width = 2    # Width at the top of the pillar
    pillar_height = 4
    pillar_offset_from_edge = 1.5 # approximate
    pillar_spacing = (base_width - 2 * pillar_offset_from_edge - 3*(pillar_bottom_width) ) / 3

    # Main rectangle
    base = c << gf.components.rectangle(size=(base_width, base_height), layer=(1, 0), centered=True)

    # Bottom connector
    connector = c << gf.components.rectangle(size=(connector_width, connector_height), layer=(1, 0), centered=True)
    connector.movey(-base_height/2 - connector_height/2)

    # Pillars at the top (Trapezoids)
    for i in range(4):
        # Create the trapezoid pillar
        rect = gf.components.rectangle(size=(pillar_bottom_width, pillar_height), layer=(1, 0), centered=True)
        triangle = gf.components.triangle(x=(pillar_bottom_width - pillar_top_width) / 2, y=pillar_height, layer=(1, 0))  # Create triangle for the sides

        pillar = boolean(rect, triangle, operation="not", layer=(1,0))
        pillar = boolean(pillar, gf.geometry.rotate(gf.geometry.mirror(triangle)), operation="not", layer=(1,0))


        pillar_ref = c << pillar

        x_pos = -base_width/2 + pillar_offset_from_edge + i * (pillar_bottom_width + pillar_spacing)
        pillar_ref.move((x_pos, base_height/2 + pillar_height/2))



    return c

if __name__ == "__main__":
    device = my_device()
    device.show()
    # Optional: Save the component to a GDS file
    device.write_gds("my_device.gds")