import gdsfactory as gf
from gdsfactory.components import bend_euler, straight, rectangle
from gdsfactory.path import smooth

@gf.cell
def stylized_waveguide():
    """Stylized waveguide shape."""
    c = gf.Component("stylized_waveguide")
    xs = gf.cross_section.cross_section(width=0.5)

    # Define path points
    p = gf.Path()
    p.append(gf.path.straight(length=20))
    p.append(gf.path.arc(radius=5, angle=45))
    p.append(gf.path.straight(length=5))
    path = p

    # Extrude the path
    wg = c << path.extrude(cross_section=xs)
    wg.rotate(-90)

    # Add a rectangle near the second bend
    rect = c << rectangle(size=(3, 1), layer=(1, 0)) # Adjust size as needed
    rect.move((5, 8)) # Adjust position as needed
    rect.rotate(-90)

    # Add ports for easy connection
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])

    return c


if __name__ == "__main__":
    sw = stylized_waveguide()
    sw.write_gds("stylized_waveguide.gds")
    sw.show()
    print("GDS file 'stylized_waveguide.gds' created.")