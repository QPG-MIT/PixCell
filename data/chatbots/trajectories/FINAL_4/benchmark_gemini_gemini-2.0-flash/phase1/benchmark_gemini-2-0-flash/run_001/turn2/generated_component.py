import gdsfactory as gf
from gdsfactory.components import bend_euler, straight


@gf.cell
def wavy_channel(width: float = 3, wavelength: float = 18, bend_radius: float = 10):
    """
    Creates a continuous wavy channel using gdsfactory.

    Args:
        width: The width of the channel in um.
        wavelength: The wavelength of the wave in um (approximately straight segment length).
        bend_radius: The radius of the bends.
    """

    c = gf.Component("wavy_channel")

    # Define cross section parameters
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # Calculate amplitude (vertical displacement)
    amplitude = width

    # Number of wave cycles
    num_cycles = 2

    # Start with a straight segment
    straight_start = c << straight(length=wavelength/2, cross_section=xs)
    current_port = straight_start.ports["o2"]

    for i in range(num_cycles):
        # Create a bend up
        bend_up = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
        bend_up.connect("o1", current_port)
        current_port = bend_up.ports["o2"]

        # Create a straight segment
        straight_mid = c << straight(length=wavelength, cross_section=xs)
        straight_mid.connect("o1", current_port)
        current_port = straight_mid.ports["o2"]
        
        #Create a bend down
        bend_down = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
        bend_down.connect("o1", current_port)
        current_port = bend_down.ports["o2"]
        
        # Another straight
        straight_mid2 = c << straight(length=wavelength, cross_section=xs)
        straight_mid2.connect("o1", current_port)
        current_port = straight_mid2.ports["o2"]
        
    bend_up_last = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_up_last.connect("o1", current_port)
    current_port = bend_up_last.ports["o2"]
    
        # End with a final straight
    straight_end = c << straight(length=wavelength/2, cross_section=xs)
    straight_end.connect("o1", current_port)
    current_port = straight_end.ports["o2"]


    # Add ports at the start and end
    c.add_port("o1", port=straight_start.ports["o1"])
    c.add_port("o2", port=straight_end.ports["o2"])

    return c


if __name__ == "__main__":
    c = wavy_channel()
    c.show()
    c.write_gds("wavy_channel.gds")