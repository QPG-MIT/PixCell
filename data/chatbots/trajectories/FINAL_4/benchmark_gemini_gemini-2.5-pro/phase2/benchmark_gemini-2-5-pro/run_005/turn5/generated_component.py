import gdsfactory as gf
import numpy as np

@gf.cell
def create_varying_width_wg(
    length: float = 18.0,
    max_width: float = 3.0,
    min_width: float = 1.0,
):
    """
    Creates a single straight waveguide with a sinusoidally varying width.
    The waveguide is widest at the center and narrowest at the ends,
    matching the target shape of a single component with wavy boundaries.

    Args:
        length: The horizontal length of the waveguide.
        max_width: The maximum width at the center of the device.
        min_width: The minimum width at the ends of the device.
    """
    c = gf.Component("varying_width_wg")

    # 1. A straight path defines the centerline of the waveguide.
    p = gf.path.straight(length=length)

    # 2. Define a function that returns the width of the waveguide.
    # FIX: The function signature must accept three arguments (t, width1, width2)
    # as required by the gdsfactory API for a custom width_type.
    def width_function(t: float, width1: float, width2: float) -> float:
        """
        Calculates the width using a cosine function.
        - t: normalized position along the path (0 to 1).
        - width1, width2: start and end widths from the transition (unused here).

        The calculation uses max_width and min_width from the parent scope
        to create the desired sinusoidal profile.
        """
        amplitude = (max_width - min_width) / 2
        average_width = (max_width + min_width) / 2
        width = average_width - amplitude * np.cos(2 * np.pi * t)
        return width

    # 3. Create a Transition object that uses our custom width function.
    # The start and end cross-sections are identical, defined by min_width.
    xs_min = gf.cross_section.cross_section(width=min_width)
    transition = gf.path.transition(
        cross_section1=xs_min,
        cross_section2=xs_min,
        width_type=width_function,
    )

    # 4. Extrude the straight path using the transition object.
    waveguide = gf.path.extrude_transition(p, transition=transition)

    # 5. Add the generated waveguide shape to the component.
    wg_ref = c << waveguide

    # 6. Add ports to the component's ends.
    c.add_port("o1", port=wg_ref.ports["o1"])
    c.add_port("o2", port=wg_ref.ports["o2"])

    return c


# Main execution block to generate and display the GDS.
if __name__ == "__main__":
    # Parameters are derived from the device footprint constraint [18, 3] um
    # and visual inspection of the target image.
    device = create_varying_width_wg(
        length=18.0,
        max_width=3.0,
        min_width=1.0,
    )
    device.show()

    # Write the final GDS file.
    device.write_gds("varying_width_wg.gds")