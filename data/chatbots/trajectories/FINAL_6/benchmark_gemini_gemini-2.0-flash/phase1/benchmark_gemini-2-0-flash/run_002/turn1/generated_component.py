import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell(check_instances=False)
def cross_flower(length=4.7, width=0.7, stem_width=0.3):
    """
    Creates a flower-like cross shape using GDSFactory parametric functions.
    """
    c = gf.Component("cross_flower")

    # Create the four petals
    petal_width = length - 2 * stem_width  # Adjust petal width for the stem
    petal_component = gf.components.ellipse(radii=(petal_width / 2, width))
    petal = c << petal_component
    petal.rotate(45) # Rotate for leaf shape

    # Adjust petal position to create a flower-like pattern
    petal1 = c << petal_component
    petal1.rotate(45)  # Rotate 45 degrees

    petal2 = c << petal_component
    petal2.rotate(135)  # Rotate 135 degrees

    petal3 = c << petal_component
    petal3.rotate(225)  # Rotate 225 degrees

    petal4 = c << petal_component
    petal4.rotate(315)  # Rotate 315 degrees

    # Create the stems
    stem_length = (length - petal_width) / 2 # Calculate stem length
    stem_component = rectangle(size=(stem_width, stem_length))
    stem = c << stem_component

    stem1 = c << stem_component
    stem1.move((0, petal_width / 2 + stem_length / 2))  # Center at top

    stem2 = c << stem_component
    stem2.rotate(90)
    stem2.move((-petal_width / 2 - stem_length / 2, 0)) # Center at left

    stem3 = c << stem_component
    stem3.move((0, -petal_width / 2 - stem_length / 2)) # Center at bottom
    
    stem4 = c << stem_component
    stem4.rotate(90)
    stem4.move((petal_width / 2 + stem_length / 2, 0))  # Center at right

    # Return the component
    return c


if __name__ == "__main__":
    c = cross_flower()
    c.show(show_ports=True)