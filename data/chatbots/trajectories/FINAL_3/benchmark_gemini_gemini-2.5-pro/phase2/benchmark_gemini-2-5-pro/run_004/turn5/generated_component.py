import gdsfactory as gf

@gf.cell
def create_directional_coupler():
    """
    Creates a directional coupler with two waveguides that come into close
    proximity in a central coupling region, and then separate again.

    This structure is built using the high-level `gf.components.coupler`
    component, which encapsulates the necessary S-bends and the straight
    coupling section, ensuring the correct parallel topology.
    """
    # --- 1. Parameter Definition ---
    # Parameters are derived from the device footprint and visual inspection.
    footprint_x = 120.0
    footprint_y = 4.0
    wg_width = 0.5

    # The `gf.components.coupler`'s `dy` parameter is the center-to-center
    # vertical separation of the input/output ports. The total component height
    # will be dy + wg_width. To fit within the footprint, we set:
    dy = footprint_y - wg_width

    # The gap is the edge-to-edge separation in the coupling region.
    # This is an estimated value based on typical coupler designs.
    gap = 0.2

    # The total length (footprint_x) is composed of two bend sections of length `dx`
    # and one straight coupling section of `length`. We choose a reasonable
    # length for the coupling section to match the target's proportions
    # and calculate dx accordingly.
    coupling_length = 40.0
    dx = (footprint_x - coupling_length) / 2.0

    # Define the waveguide cross-section.
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- 2. Component Instantiation & Assembly ---
    c = gf.Component("directional_coupler")

    # Instantiate the coupler primitive with our calculated parameters.
    # This single component handles the bends, gap, and straight section.
    coupler_device = gf.components.coupler(
        length=coupling_length,
        gap=gap,
        dy=dy,
        dx=dx,
        cross_section=xs
    )

    # Add the coupler instance to our component. The primitive is
    # already centered at (0,0), which is the desired placement.
    coupler_ref = c << coupler_device

    # Expose the ports of the coupler instance as the top-level ports.
    # The port names (o1, o2, o3, o4) match the standard convention
    # for a 4-port coupler (top-left, bot-left, top-right, bot-right).
    c.add_ports(coupler_ref.ports)

    return c

if __name__ == "__main__":
    # Create an instance of the device cell.
    device = create_directional_coupler()

    # Write the component geometry to a GDSII file.
    device.write_gds("directional_coupler.gds")

    # Optional: Display the component in the KLayout-based viewer.
    device.show()