import gdsfactory as gf

@gf.cell
def bent_waveguide_with_rectangle(bend_radius: float = 10.0, rectangle_width: float = 5.0, rectangle_length: float = 20.0, cross_section="strip"):
    """
    Creates a bent waveguide with a rectangle shape nearby.

    Args:
        bend_radius: Radius of the bend.
        rectangle_width: Width of the rectangle.
        rectangle_length: Length of the rectangle.
        cross_section: cross section name (default: "strip")
    """
    c = gf.Component()

    # Load the cross-section
    xs = gf.get_cross_section(cross_section)

    # Create a bend (Euler bend for smoother transition)
    bend = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend.rotate(90)

    # Create a straight waveguide segment attached to the bend's input
    straight1 = c << gf.components.straight(length=50, cross_section=xs)  # Adjusted length for visibility
    straight1.connect("o2", bend.ports["o1"])

    # Create a rectangle
    rectangle = c << gf.components.rectangle(size=(rectangle_length, rectangle_width))

    # Position the rectangle near the bend
    rectangle.movex(straight1.xmin + bend_radius / 2 - rectangle_length / 2) #position the rectangle to be above bend vertically centered
    rectangle.movey(straight1.ymax + 10)

    # Add ports
    c.add_port("o1", port=straight1.ports["o1"])
    c.add_port("o2", port=bend.ports["o2"])

    return c

if __name__ == "__main__":
    # Example usage
    component = bent_waveguide_with_rectangle()
    component.show()
    component.write_gds("bent_waveguide_with_rectangle.gds")