import gdsfactory as gf

@gf.cell
def symmetric_coupler() -> gf.Component:
    """
    Creates a symmetric coupler geometry with a specified footprint of 18x3 um.
    The structure is composed of S-bends joining seamlessly.
    """
    c = gf.Component()
    
    # Define standard waveguide cross section
    # Width = 0.5um fits the 3um total height constraint
    # when combined with our calculated 1.25um shifts.
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Calculate geometry dimensions to fit 18x3 um footprint
    # Total length = 18 -> Each S-bend half is 9 um long
    # Total height = 3 -> Y-bounds are -1.5 to +1.5. Center of ports are at +/- 1.25.
    length_half = 9.0
    y_shift = 0.9
    port_y_offset = 1.25

    # Create S-bend primitives
    bend_down = gf.components.bend_s(size=(length_half, -y_shift), cross_section=xs)
    bend_up = gf.components.bend_s(size=(length_half, y_shift), cross_section=xs)

    # --- Top Waveguide Arm ---
    top_in = c << bend_down
    top_out = c << bend_up

    # Position the input port of the top waveguide
    top_in.move((0, port_y_offset))
    # Seamlessly connect the outward bend to the inward bend
    top_out.connect("o1", top_in.ports["o2"])

    # --- Bottom Waveguide Arm ---
    bot_in = c << bend_up
    bot_out = c << bend_down

    # Position the input port of the bottom waveguide symmetrically
    bot_in.move((0, -port_y_offset))
    # Seamlessly connect the outward bend to the inward bend
    bot_out.connect("o1", bot_in.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=top_in.ports["o1"])
    c.add_port("o2", port=bot_in.ports["o1"])
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the created device
    device = symmetric_coupler()
    
    # Write to GDS file to fix the "No GDS file produced" error
    device.write_gds("symmetric_coupler.gds")