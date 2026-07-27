import gdsfactory as gf

@gf.cell
def directional_coupler(
    length: float = 40.0,
    gap: float = 0.5,
    dy: float = 3.2,
    dx: float = 40.0,
    waveguide_width: float = 0.8,
) -> gf.Component:
    """
    Generates a directional coupler with smooth S-bends.

    This component is designed to match the target image, which depicts a
    classic directional coupler. It consists of two input waveguides that are
    brought close together using S-bends, run parallel for a specified
    coupling length, and then are separated again by S-bends.

    This implementation uses the high-level `gf.components.coupler` primitive,
    which is the standard and most robust way to create this geometry in
    gdsfactory. It correctly creates the parallel coupling section that was
    missing in the previous sinusoidal crossover attempt.

    Args:
        length: The length of the straight, parallel coupling section.
        gap: The edge-to-edge distance between waveguides in the coupling section.
        dy: The vertical center-to-center separation of the input/output ports.
        dx: The horizontal length of the S-bend transition sections.
        waveguide_width: The width of the waveguides.
    """
    # Define the waveguide cross-section based on the provided width.
    xs = gf.cross_section.cross_section(width=waveguide_width)

    # Instantiate the pre-built gdsfactory directional coupler component.
    # This component encapsulates the S-bends and the straight coupling
    # section, perfectly matching the target geometry.
    c = gf.components.coupler(
        length=length,
        gap=gap,
        dy=dy,
        dx=dx,
        cross_section=xs
    )
    return c


if __name__ == "__main__":
    # Create an instance of the directional coupler.
    # The parameters are chosen to match the provided footprint constraint
    # of [120, 4] um.
    # Total length = dx + length + dx = 40 + 40 + 40 = 120 um.
    # Total height = dy + waveguide_width = 3.2 + 0.8 = 4.0 um.
    device = directional_coupler()

    # Show the component in the KLayout viewer for verification.
    device.show()

    # Write the component to a GDSII file.
    device.write_gds("directional_coupler.gds")