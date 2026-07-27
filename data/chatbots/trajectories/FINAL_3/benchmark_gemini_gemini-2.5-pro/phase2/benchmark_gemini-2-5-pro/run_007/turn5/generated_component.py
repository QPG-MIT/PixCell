import gdsfactory as gf

@gf.cell
def tapered_directional_coupler(
    length: float = 40.0,
    gap: float = 0.5,
    dx: float = 40.0,
    width_wide: float = 1.0,
    width_narrow: float = 0.5,
    dy: float = 3.0,
) -> gf.Component:
    """
    Generates a directional coupler with waveguides that taper along the
    S-bend sections.

    This component is constructed by assembling tapered S-bends and straight
    waveguide sections. It matches the target image, which shows waveguides
    that are wider at the input/output ports and narrower in the central
    coupling region. The width transition occurs smoothly over the S-bends.

    Args:
        length: The length of the straight, parallel coupling section.
        gap: The edge-to-edge distance between waveguides in the coupling section.
        dx: The horizontal length of the S-bend transition sections.
        width_wide: The width of the waveguides at the input/output ports.
        width_narrow: The width of the waveguides in the coupling section.
        dy: The vertical center-to-center separation of the input/output ports.
    """
    c = gf.Component()

    # 1. Create the primitive components required for assembly.

    # Calculate the vertical shift needed for the S-bend path.
    # It transitions from the port separation (dy) to the coupling separation.
    s_bend_dy = (dy - (gap + width_narrow)) / 2

    # Define the wide and narrow cross-sections.
    xs_wide = gf.cross_section.cross_section(width=width_wide)
    xs_narrow = gf.cross_section.cross_section(width=width_narrow)

    # Create a Transition object. This is a special type of cross_section
    # that describes a change from one cross_section to another.
    # Using width_type='sine' ensures a smooth transition.
    taper_xs = gf.cross_section.Transition(
        cross_section1=xs_wide, cross_section2=xs_narrow, width_type="sine"
    )

    # Create the tapered S-bend component by passing the Transition
    # object to the `cross_section` argument of the standard S-bend component.
    tapered_bend = gf.components.bend_s(
        size=(dx, s_bend_dy), cross_section=taper_xs
    )

    # Create the narrow straight section for the coupling region.
    straight_coupler = gf.components.straight(length=length, cross_section=xs_narrow)

    # 2. Assemble the full device by adding and connecting the primitives.
    b_in_top = c << tapered_bend
    b_in_bot = c << tapered_bend
    s_top = c << straight_coupler
    s_bot = c << straight_coupler
    b_out_top = c << tapered_bend
    b_out_bot = c << tapered_bend

    # Position and connect the top waveguide path.
    s_top.connect("o1", b_in_top.ports["o2"])
    b_out_top.mirror()
    b_out_top.connect("o2", s_top.ports["o2"])

    # Position and connect the bottom waveguide path.
    b_in_bot.mirror(p1=(0, 0), p2=(1, 0))
    s_bot.connect("o1", b_in_bot.ports["o2"])
    b_out_bot.mirror()
    b_out_bot.mirror(p1=(0, 0), p2=(1, 0))
    b_out_bot.connect("o2", s_bot.ports["o2"])

    # 3. Add the component's external ports.
    c.add_port("o1", port=b_in_top.ports["o1"])
    c.add_port("o2", port=b_in_bot.ports["o1"])
    c.add_port("o3", port=b_out_bot.ports["o1"])
    c.add_port("o4", port=b_out_top.ports["o1"])

    return c


if __name__ == "__main__":
    # Parameters are chosen to match the footprint [120, 4] and visual cues.
    # Total length = dx + length + dx = 40 + 40 + 40 = 120 um.
    # Total height = dy + width_wide = 3.0 + 1.0 = 4.0 um.
    device = tapered_directional_coupler(
        length=40.0,
        gap=0.5,
        dx=40.0,
        width_wide=1.0,
        width_narrow=0.5,
        dy=3.0,
    )
    device.show()
    device.write_gds("tapered_directional_coupler.gds")