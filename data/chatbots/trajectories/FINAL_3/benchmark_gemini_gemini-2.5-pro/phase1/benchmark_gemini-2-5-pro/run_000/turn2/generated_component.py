import gdsfactory as gf

@gf.cell
def sine_taper(length: float, width1: float, width2: float) -> gf.Component:
    """
    Creates a taper component with a sinusoidal width transition to create a
    flared, adiabatic shape. This replaces the linear gf.components.taper.

    Args:
        length: The length of the taper.
        width1: The width at the start of the taper.
        width2: The width at the end of the taper.
    """
    # Define the path for the taper, which is a simple straight line
    taper_path = gf.path.straight(length=length)

    # Define the cross-sections for the start and end of the taper
    xs1 = gf.cross_section.cross_section(width=width1)
    xs2 = gf.cross_section.cross_section(width=width2)

    # Create the transition profile. The 'sine' width_type produces the
    # desired flared shape seen in the target image.
    transition = gf.path.transition(
        cross_section1=xs1, cross_section2=xs2, width_type="sine"
    )

    # Extrude the path with the sinusoidal transition to create the component
    taper_component = gf.path.extrude_transition(p=taper_path, transition=transition)
    return taper_component


def create_component() -> gf.Component:
    """
    Recreates the flared directional coupler geometry based on the provided
    image and footprint constraints.
    """

    # --- 1. Define Parameters from Footprint and Image Analysis ---

    # Overall footprint dimensions from the task constraint
    footprint_x = 120.0
    footprint_y = 4.0

    # Define geometric parameters. Port width is increased to match the flare.
    taper_length = 10.0
    port_width = 2.0  # Increased to match the visually wider flared port
    wg_width = 0.5
    gap = 0.2

    # Recalculate vertical separation based on the new, wider port
    # footprint_y = dy (center-to-center) + port_width
    dy = footprint_y - port_width  # 4.0 - 2.0 = 2.0

    # Central coupler dimensions remain the same to maintain total length
    coupler_dx = 20.0
    coupler_length = 60.0

    # --- 2. Create the Component using the Assembly Pattern ---

    c = gf.Component("flared_directional_coupler")
    xs = gf.cross_section.cross_section(width=wg_width)

    # Create the central coupler primitive (this part is unchanged)
    coupler_core = gf.components.coupler(
        length=coupler_length,
        gap=gap,
        dy=dy,
        dx=coupler_dx,
        cross_section=xs,
    )

    # Create the custom flared taper primitive using our new function
    taper = sine_taper(length=taper_length, width1=wg_width, width2=port_width)

    # --- 3. Assemble the Primitives ---

    coupler_ref = c << coupler_core

    # Input tapers (mirrored)
    taper_in_bot = c << taper
    taper_in_top = c << taper
    taper_in_bot.mirror()
    taper_in_top.mirror()

    taper_in_bot.connect("o1", coupler_ref.ports["o1"])
    taper_in_top.connect("o1", coupler_ref.ports["o2"])

    # Output tapers
    taper_out_top = c << taper
    taper_out_bot = c << taper

    taper_out_top.connect("o1", coupler_ref.ports["o3"])
    taper_out_bot.connect("o1", coupler_ref.ports["o4"])

    # --- 4. Expose the External Ports ---

    c.add_port("o1", port=taper_in_bot.ports["o2"])
    c.add_port("o2", port=taper_in_top.ports["o2"])
    c.add_port("o3", port=taper_out_top.ports["o2"])
    c.add_port("o4", port=taper_out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the component by calling the creation function
    my_component = create_component()
    
    # Write the component to a GDS file in the current directory
    my_component.write_gds("flared_directional_coupler.gds")

    # To visualize the component, you can uncomment the line below
    # my_component.show()